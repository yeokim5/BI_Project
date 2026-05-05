# BI Project — Interview Study Guide
> Goal: understand every decision, not every line. Speak from architecture, not syntax.

---

## How to use this file

For each section: **read it once, close it, say it out loud**. If you can't say it without looking, read it again.  
You do NOT need to memorize pandas syntax. You need to own the "why."

---

## Part 1 — The Big Picture (know this cold)

### What the pipeline does (one sentence)
Combines on-the-books hotel reservations with local event data to produce a 90-day occupancy and RevPAR forecast for two hotels — explainable at every step, no black-box models.

### The 3-stage architecture
```
[1_data_prep.py]     Load OTB + Events CSVs → raw merged_data.csv
      ↓
[1b_data_patch.py]   Audit + fix data integrity → reconciled_data.csv
      ↓
[2_forecast_model.py] OTB + Pickup + Event Weight → forecast_90days.csv + charts
```

### Why 3 files instead of 1?
Each stage is independently auditable. If stage 2 fails the assert, stage 3 never runs on corrupt data. This mirrors how you'd build it in production — not a Jupyter notebook you can't version or test.

---

## Part 2 — `1_data_prep.py` (5 min — least critical)

### What it does
- Loads both CSVs, validates required columns exist
- Parses date columns, derives `lead_time = business_date - snapshot_date`
- Left-joins OTB to Events on `(location == market, business_date == event_date)`
- Logs fan-out if it detects row count growth
- Reports data quality summary

### One key decision: why left join?
Every OTB row must survive the join. If a hotel date has no event, it still needs to exist in the forecast with `event_weight = 0`. An inner join would silently delete non-event dates.

### What this file DOESN'T do
It detects fan-out but doesn't fix it. That's intentional — detect in stage 1, fix in stage 2. Separation of concerns.

---

## Part 3 — `1b_data_patch.py` (★ most important — own every function)

### What it does
Fixes three problems found in the raw data before any forecast runs:
1. Fan-out from multi-event dates
2. Occupancy outliers (>1.0 from overbooking)
3. Revenue integrity check (passes)

---

### Function 1: `aggregate_events()` — THE fan-out fix

**The problem:** Boston can have 22 events on one date (e.g., Sept 17). A raw join on `(market, date)` duplicates one OTB row 22 times → 4,732 rows becomes 28,276. Every downstream sum (visitors, event lift) is wrong by 6×.

**The fix:** Pre-aggregate events to one row per `(market, date)` BEFORE joining. Sum visitors, count events, keep dominant category.

**The guard:** Line 93 — `assert len(merged) == len(df_otb)` — hard crash if fan-out still happens.

**Say it out loud:** *"Naive join exploded 4,732 rows to 28,276 — a 6× fan-out. I pre-aggregated events to 841 summaries before the join. The assert on line 93 is the proof it worked."*

---

### Function 2: `fix_occupancy_outliers()` — cap, don't drop

**The problem:** hotel_b (Boston) has 32 rows where `occupancy > 1.0`. This means they sold more rooms than capacity — real overbooking, not a data error.

**The decision: cap at 1.0, not drop the rows**
- Dropping removes real booking history → biases the pickup rate calculation downward
- rooms_sold is left untouched (the truth is preserved)
- Only the *ratio* is capped for model math safety
- Flagged for operations review as a separate recommendation

**What you rejected:** Dropping rows, imputing a different value, raising an exception.

**Say it out loud:** *"Overbooking is a normal hotel practice — dropping those rows would have corrupted the pickup rate. I preserved rooms_sold, capped the ratio at 1.0 for model safety, and flagged it to operations."*

---

### Function 3: `check_revenue_integrity()` — the one that passed

**What it checks:** `revenue_sold` should equal `rooms_sold × adr_sold`. Allows ±$1.50 for rounding.

**Result:** Max delta = $1.36. Passed. All revenue discrepancies within tolerance.

**Why this matters in an interview:** Shows you audited the data from all angles, not just the bugs you already knew about.

---

### Function 4: `validate_final()` — the final gate

**What it checks:**
- Zero duplicate rows on true PK: `(hotel_code, snapshot_date, business_date)`
- Occupancy all within [0, 1] after fix
- No nulls in key forecast columns

**Key insight:** The PK has 3 columns, not 2, because the OTB data is a booking *curve* — the same future date appears up to 13 times as new snapshots arrive.

---

## Part 4 — `2_forecast_model.py` — THE formula

### The forecast formula (memorize this)

```
forecast_occupancy = current_occupancy + pickup_rate + event_weight
                     (capped at 1.0 — you can't have >100% occupancy)

forecast_revpar    = forecast_occupancy × current_adr
```

Three additive fractions of total rooms. Clean units. Auditable line by line.

---

### Component 1: `current_occupancy`
`rooms_sold / total_rooms` at the latest snapshot. What's already on the books today.

---

### Component 2: `pickup_rate` — how you derived it (key question)

**What it is:** The fraction of total rooms *still expected to book* between now and arrival, based on historical pattern.

**How you computed it:**
1. The OTB data has 26 snapshot dates. Same future date appears at multiple lead times as bookings build.
2. For each `(hotel, business_date)`: find `rooms_sold` at check-in (lead_time ≤ 5 days)
3. For each lead-time bucket (7, 14, 21, 30, 45, 60, 90 days out): compute `additional = rooms_at_checkin − rooms_at_bucket`
4. Average across all business dates → pickup rate table

**For any lead time between buckets:** linear interpolation.

**Why not ML here?** 26 snapshots × 2 hotels isn't enough data. A model would overfit. Averages are both more honest and more interpretable.

**The pickup rates (know directionally):**
| Lead Time | Santa Monica | Boston  |
|-----------|-------------|---------|
| 90 days   | +36.6%      | +56.3%  |
| 60 days   | +33.1%      | +52.3%  |
| 30 days   | +24.5%      | +39.6%  |
| 14 days   | +15.6%      | +22.0%  |
| 7 days    | +9.0%       | +11.6%  |

**Business meaning:** Boston fills up much faster than Santa Monica. Rate decisions need to be made earlier.

---

### Component 3: `event_weight` — THE formula to know by heart

```python
visitor_density = total_visitors / total_rooms
event_weight    = min(visitor_density / 1000, 0.15)
```

**Why normalize by total_rooms?** Raw visitor count is meaningless without scale. 2M visitors means something different to a 238-room hotel vs a 5,000-room convention center.

**Why divide by 1,000?** Converts visitor-per-room density to occupancy lift. 1 unit = 0.1% occupancy lift.

**Why cap at 0.15 (15%)?** Prevents a single mega-event from pushing any forecast to 100% regardless of actual OTB. The cap is a judgment call — in production, calibrate against historical event performance.

**What you rejected:** Linear scaling without a cap (would produce impossible >100% forecasts for large events).

**Real example — Sept 17, Hans Zimmer concert:**
- 72,300 visitors / 238 rooms = density 303.8
- 303.8 / 1000 = 0.304 → capped at 0.15
- OTB was 34.9%, pickup adds 54.8%, event adds 15% → 100% forecast. Correct.

---

### Why no ML at all?

Three reasons, say any one:
1. **Data volume:** 4,732 rows, 2 hotels, 26 snapshots. Not enough to train without overfitting.
2. **Explainability:** A GM asks "why is July 11 at 100%?" — you need an auditable answer, not a probability score.
3. **JD fit:** The brief said "share your logic and approach." A black-box model is the opposite of that.

---

## Part 5 — The Numbers (memorize cold)

### Hotel A — Santa Monica
- 315 rooms
- Avg 90-day occupancy: **62.0%**
- Avg 90-day RevPAR: **$157.46**
- Peak: July 4 (Santa Monica Parade) → 96.5% occ, $237 RevPAR, 12K visitors

### Hotel B — Boston
- 238 rooms
- Avg 90-day occupancy: **88.7%**
- Avg 90-day RevPAR: **$298.91**
- **26 total sellout dates** in the 90-day window
- Top 4 rate-fencing targets:
  - Sept 9: $427 RevPAR (Future of Passive Housing)
  - Sept 16: $422 RevPAR (Conference cluster)
  - Sept 17: **$432 RevPAR** ← Hans Zimmer (highest)
  - Sept 26: $405 RevPAR (Conference cluster)

### Data audit numbers
- Raw OTB: **4,732 rows** (26 snapshots × 2 hotels)
- Events: **7,197 records**
- Fan-out if unfixed: **4,732 → 28,276** (6× explosion)
- Post-aggregate: **841 event-day summaries** (clean 1:1 join)
- Occupancy outliers fixed: **32 rows**
- Revenue check max delta: **$1.36** (tolerance: $1.50) → passed

---

## Part 6 — The Recommendations (anchor every one to dollars)

### Rec 1 — Boston rate fencing
- Target: Sept 9, 16, 17, 26 (all at 100% occ, ADR ~$420)
- Move ADR from ~$422 to $480–$520
- **Math:** ~$78 lift × 238 rooms × 4 nights ≈ **$74,600 incremental**
- Timeline: 24–48 hours in PMS

### Rec 2 — Santa Monica soft window
- Target: Aug 4 – Sep 14 (52–65% occ, thin event calendar)
- Tactic: 3-night leisure discounts, direct-book corporate rates, group quotes
- Launch: 45–60 days before (late June) — steepest pickup is 30–60 day window
- **Math:** +8–10 occ points × 42 days ≈ 1,000–1,300 room nights ≈ **$258K–$335K**

### Rec 3 — Overbooking review (zero cost)
- 32 rows with negative `left_to_sell` in Boston data
- Question: intentional overbooking strategy, or system error?
- If intentional: document displacement costs and walk procedures
- If error: tighten controls
- Timeline: flag to ops this week

---

## Part 7 — Q&A Drills

**Q: How do you know the AI didn't write buggy logic?**  
"I never assume it didn't. That's the point of the `/reconcile-data` layer. I test outputs against business constraints — occupancy must be 0–100%, revenue must balance within $1.50, row count must not change during merge. Output fails → agent rewrites. Same principle I built into OMEL AI's safety layer."

**Q: Why no machine learning?**  
"4,732 rows across 2 hotels isn't enough to train without overfitting. More importantly, this needs to be explainable to a GM asking 'why is July 11 flagged at 100%?' Transparent formula beats an overfit model in this data environment."

**Q: Can you explain what the pickup rate actually is?**  
"It's the fraction of total rooms I expect to still book between today and arrival, based on historical patterns in the OTB data. The data has 26 snapshots — I can see how the same future date fills up over time. That's the pickup curve."

**Q: What's the 15% cap on events?**  
"Without a cap, a mega-event like Boston Harborfest (2M visitors) would push every hotel in Boston to 100% regardless of OTB. The cap is a defensible ceiling — I'd calibrate it with historical event-vs-actual-occupancy data in production."

**Q: How would you scale this to all Pebblebrook properties?**  
"The code is modular by design — each function takes a hotel code and config. Adding a hotel is a config change, not a rebuild. I'd wrap these in FastAPI endpoints, containerize with Docker, run nightly via GitHub Actions, feed Tableau directly."

**Q: Why did you cap occupancy instead of dropping overbooking rows?**  
"Dropping 32 rows removes real historical data from the pickup rate calculation — it would bias the rate downward. The overbooking happened; rooms_sold is preserved. I only cap the ratio so model math doesn't break. The ops question (is this intentional?) is Rec 3."

**Q: You used AI to build this — can you actually explain the logic?**  
"The syntax was typed by an agent; the architecture was mine. I specified: explainable model only, weight events by visitor density relative to room count, cap at 15%, derive pickup from historical snapshots. I designed the pipeline; the agent wrote the pandas. That distinction is the whole point."

---

## Part 8 — The Trap to Avoid

Reid asks: *"What does line 47 do?"*

Don't defend syntax. Say:
> *"That's the pandas syntax the agent wrote — I specified the constraint. The constraint was [X], because [business reason]."*

That's a stronger answer than reciting syntax, and it's honest.

---

## Part 9 — Pre-Interview Checklist (15 min before)

- [ ] Open PRESENTATION.md + charts folder side by side
- [ ] Have `1b_data_patch.py` open, ready to show lines 55–95 (aggregate + assert)
- [ ] Memorize 3 dollar figures: **$75K**, **$258–335K**, **zero-cost audit**
- [ ] Memorize 4 Boston sellout dates: **Sept 9, 16, 17, 26**
- [ ] Memorize 2 averages: **62% / $157** (SM) and **88.7% / $299** (BOS)
- [ ] Memorize event formula: **min(visitors / rooms / 1000, 0.15)**
- [ ] Memorize fan-out: **4,732 → 28,276** (6× error, caught and fixed)
- [ ] Rehearse opening pitch once out loud
- [ ] Rehearse Q7 (AI authorship question) once out loud

---

## Part 10 — The One-Sentence Summary

> "A transparent, auditable 90-day forecast: OTB plus empirically-derived pickup rates plus event lift — every number traces to source data, every stage verified before the next ran."

Say that at the end. Own it.

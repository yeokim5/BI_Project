# Pebblebrook 90-Day Forecast — Methodology & AI-Augmented Workflow

**Two hotels · 90-day horizon · Transparent model · Auditable end-to-end**

---

## 1. The Bottom Line

**Constraints:** 90 minutes · 2 datasets (4,732 rows) — no black-box ML, every number traceable.

**Three actions the model surfaces — combined upside ~$451K–$528K incremental revenue:**

| Market | Action | Revenue |
|---|---|---|
| Boston | Tiered pricing: 6 sellouts + 12 compression dates | ~$193K |
| Santa Monica | Demand stimulation (Aug 4–Sep 13 soft window) | ~$258K–$335K |
| Boston | Resolve overbooking anomaly (Apr 19–21) | Data integrity |

The rest of this document shows how the model earns the right to make those calls — starting with how I keep the data honest, then the AI workflow, then the math, then the V2 roadmap.

---

## 2. Data Gatekeeper — "One Version of the Truth"

A forecast built on unreconciled data is a confident lie. The `/reconcile-data` skill ran as a **non-negotiable gate** before any forecasting code executed — same principle I'd apply on day one for the Property Data Portal.

| Check | Finding | Decision |
|---|---|---|
| Naive market+date event join | **4,732 → 28,276 rows** (6× fan-out) | Pre-aggregated events to 841 day-summaries before the join |
| Occupancy outliers | **32 rows > 100%** (Boston Apr 19–21) | Real overbooking signal — capped at 1.0, flagged for Ops |
| Revenue integrity | Max delta **$1.36** vs `rooms × ADR` | Within $1.50 rounding tolerance — accepted |
| Join keys (markets) | 100% overlap, zero orphaned records | Passed |
| Forecast formula | Manual verification on all 180 output rows | Zero residual — formula matches CSV exactly |

**In plain terms — three problems caught before a single forecast number ran:**

1. **Fan-out (the big one):** Events table had 4,732 rows. OTB had 180. A naive join produced 28,276 — data multiplied itself 6×. Fix: collapse events to one row per (market, date) first, then join. Clean.
2. **Impossible occupancy:** 32 rows over 100% on Boston Apr 19–21. Either intentional overbooking or a system bug. Capped at 100% for forecasting; flagged to Ops (this becomes Rec 3).
3. **Revenue math:** `ADR × rooms_sold` should equal `revenue_sold`. Largest gap: $1.36 — rounding, not a data error. Accepted.

**Philosophy:** I don't blindly trust data dumps. Reconciliation is a gate, not an afterthought. If the audit fails, nothing downstream runs.

---

## 3. Agentic Practitioner — How This Got Built

I act as the architect; AI agents handle syntax. Architecture first, code second. **Every AI output passes through a mathematical audit boundary before anything downstream runs.**

**Stack used here (mirrors your preferred stack — Python + FastAPI):**
- **Claude Code** (CLI) + project workspace at `.claude/`
- Two purpose-built agents — **`@pipeline-architect`** (data + forecasting), **`@business-strategist`** (presentation translation)
- One custom skill — **`/reconcile-data`** (the audit gate from §2)
- **CLAUDE.md** — project constraints (no ML, modular, explainable) loaded into every agent session

**The 5-step loop I ran for every stage:**

```
SPEC        →  Write business constraints into CLAUDE.md before any code
DECOMPOSE   →  Break problem into independent, testable stages
GENERATE    →  Delegate boilerplate (pandas joins, chart scaffolding) to agent
VERIFY      →  Run /reconcile-data — catch hallucinations at the data boundary
COMMIT      →  Only proceed to next stage after audit passes
```

**Stages in practice:**

| Stage | Agent / Skill | Output | What I verified |
|---|---|---|---|
| 🟢 Data Prep & Merge | `@pipeline-architect` | `1_data_prep.py`, `merged_data.csv` (28,276 rows) | Caught fan-out + occupancy outliers + missing event data |
| 🟡 Reconcile / Audit | `/reconcile-data` skill | `1b_data_patch.py`, `reconciled_data.csv` (4,732 rows) | Fan-out resolved, occupancy capped, integrity confirmed |
| 🟠 Forecast | `@pipeline-architect` | `2_forecast_model.py`, `forecast_90days.csv`, 3 charts | Formula audited row-by-row; zero residual |
| 🔴 Translate | `@business-strategist` | `PRESENTATION.md`, `SUMMARY.md` | Numbers cross-checked against CSV |

**How I audit AI output (directly answering the JD's cover letter prompt):**

Every output is tested against strict business boundaries — if it fails, the agent rewrites:
- Occupancy ∈ [0, 1]
- `rooms_sold + left_to_sell + ooo == total_rooms` for every row
- `revenue_sold ≈ rooms_sold × adr_sold` within $1.50 tolerance
- Event joins must not fan-out (rows in == rows out)
- If the agent can't explain **why** a number is what it is, the number doesn't ship.

This is the same hallucination-guardrail pattern I built at OMEL AI for enterprise chatbots — intercept the output, validate against domain rules, block anything that can't be proven correct. It's the layer that turns "AI-generated" into "production-trustable."

---

## 4. The Model & Results

### Three explainable components — no black box

```
Forecast Occupancy  =  OTB Occupancy  +  Pickup Rate  +  Event Weight   (cap 1.0)
Forecast RevPAR     =  Forecast Occupancy  ×  Current ADR

Event Weight        =  min( visitors / rooms / 1000 ,  0.15 )   # 15% ceiling
```

| Component | What it is | Why this choice |
|---|---|---|
| **OTB Occupancy** | Already booked — ground truth | Not a prediction. Auditable. |
| **Pickup Rate** | Expected additional bookings by arrival | **Empirically derived** from 26 OTB snapshots — not borrowed assumptions |
| **Event Weight** | Incremental occ lift from market events | Normalized by room count; capped at +15 pts so one event can't flip a forecast |

### Pickup derivation — the empirical core

For each (hotel, future date), the source contains ~13 snapshots showing bookings build toward check-in. That lets me measure pickup empirically by lead-time bucket — no external curves.

```
90 days before arrival → 32 rooms sold
60 days before arrival → 41 rooms sold
30 days before arrival → 55 rooms sold
Day of arrival         → 71 rooms sold (final count)

Pickup from 90-day-out = (71 - 32) / 100 total rooms = +39% will still book
```

Average across all historical dates → hotel's unique pickup curve. **Two distinct market personalities emerge:**

- **Boston** — steep curve, **+56.3%** pickup over 90 days → guests book late and fast → revenue calls must be made early or the window closes
- **Santa Monica** — shallow curve, **+36.6%** pickup over 90 days → guests spread bookings → more time to run promotions

The curve shape directly drives the recommendations.

![Pickup Curve](charts/chart3_pickup_curve.png)

### Results

![Occupancy Forecast](charts/chart1_occupancy_forecast.png)
![RevPAR Forecast](charts/chart2_revpar_forecast.png)

| | **Hotel A — Santa Monica** | **Hotel B — Boston** |
|---|---|---|
| Avg Occupancy | 62.0% | 88.7% |
| Avg RevPAR | $157.46 | $298.91 |
| Sellout Dates | 0 of 90 | 26 of 90 |
| Peak Date | Jul 4 → $237 RevPAR | Sep 17 (Hans Zimmer) → $432 RevPAR |

Every spike ties to a named event in `data-events.csv`. Every number traces to a specific row.

---

## 5. Recommendations — Detail Behind the Headlines

### Rec 1 — Boston Tiered Rate Program · ~$193K
Hotel B = 238 rooms. Boston pickup curve = +56% late, so compression closes the back end. Three tiers by occupancy band:

**Tier 1 — Sellouts ≥ $405 ADR · lift $80 → ~$113K**
Six confirmed sellouts at premium ADR. At 100% occ, rate is the only lever.

| Date | ADR | Driver |
|---|---|---|
| Sep 17 | $432 | Hans Zimmer |
| Sep 9  | $427 | Translational Digital Pathology Summit |
| Jul 16 | $425 | Process Dev Cell Therapies Summit |
| Jul 15 | $422 | Weird Al @ Boch Center |
| Sep 16 | $422 | LSX World Congress USA |
| Sep 26 | $405 | John Mulaney @ Boch Center |

`6 × 238 × $80 ≈ $114K`

**Tier 2 — Compression dates, occ 91–98% · lift $30 → ~$80K**
12 near-sellouts with strong ADR ($329–$416). Conservative $30 lift assumes mild attrition.

Sep 27, Sep 8, Jul 8, Jul 29, Sep 10, Sep 25, Sep 12, Jul 14, Sep 7, Aug 30, Jul 17, Sep 5

`12 × 238 × 0.94 × $30 ≈ $80K`

**Tier 3 — Watchlist, occ 85–89% (Sep 13/15/18/19/20)**
Don't lift yet. Monitor 7-day pickup velocity. Promote to Tier 2 if occ crosses 92%.

> Change executes in 24–48 hrs across PMS. Sep dates concentrate around event halo (Hans Zimmer + back-to-school conferences); Jul dates concentrate around Boch Center + biotech summits.

### Rec 2 — Santa Monica Demand Stimulation · ~$258K–$335K
**Slow window:** Aug 4 – Sep 13 (41 days). No major market events, school back in session, leisure drops. Forecast shows **59.2% occupancy** — ~4 in 10 rooms empty nightly.

**Why now:** Santa Monica guests book 45–60 days out. April–May *is* the decision window for August stays.

| | Low (8 pt lift) | High (10 pt lift) |
|---|---|---|
| Extra rooms filled per night | 25 | 31 |
| × 41 nights × $257.90 ADR | **~$265K** | **~$328K** |

8–10 pt lift from soft-period promotion is the conservative end of the 8–12 pt industry range.

### Rec 3 — Overbooking Review · Zero cost
32 source rows show negative `left_to_sell` on Boston Apr 19–21. If intentional yield strategy → document it. If system defect → it's corrupting every downstream report. The answer costs nothing and is worth knowing.

---

## 6. Roadmap — Limitations as V2 Opportunities

Stated openly so the next iteration is obvious. Each gap is a build, not a blocker:

| Gap Today | V2 Opportunity |
|---|---|
| **Not a rate forecast** — model says *where* to act, not what rate to set | Add price elasticity layer + comp-set data → optimal rate per night |
| **Not competitor-aware** | Plug in OTA(Online Travel Agency) comp-rate feed → react to market repricing |
| **Not reactive to cancellations** | Single-date re-forecast endpoint (already modular) — wire to event cancellation feed |
| **Not continuous** | Replace 26 static snapshots with live OTB stream → daily-refreshed forecast |
| **CSV output** | Pipeline already returns DataFrames — point Tableau at the FastAPI endpoint for proactive ops reporting |

**Architecture is already shaped for this.** Each stage is a function behind a clean boundary:

```
[Load CSVs]  →  [Reconcile / Audit]  →  [Forecast]  →  [Translate]
 1_data_prep      1b_data_patch          2_forecast_model    PRESENTATION.md
                  /reconcile-data
                  skill (gate)
```

- **Modular** — every stage is a function, not a script
- **FastAPI-ready** — functions slot behind REST endpoints with no refactor
- **Portable** — new hotel = one config entry, no code change
- **Dashboard-ready** — output plugs into Tableau

Same shape applies to the **Property Data Portal**: inputs → audit gate → transform → output, with AI agents doing the transform under a verification boundary. That's the workflow I'd bring on day one.

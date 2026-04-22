# Pebblebrook 90-Day Forecast — Methodology & AI-Augmented Workflow

**Two hotels · 90-day horizon · Transparent model · Auditable end-to-end**

---

## 1. How I Framed the Problem

90-minute budget. Two CSVs. Non-technical stakeholders. Three constraints drove every decision:

| Constraint | Implication |
|---|---|
| Stakeholders in Finance / Ops must understand the "why" | **No black-box ML.** Every number must trace to source. |
| 90-min build, 4,732 rows, 2 hotels | Not enough data for supervised ML without overfit. Empirical baselines win. |
| Must scale across a REIT portfolio | Modular functions, not one-off scripts. **FastAPI-ready.** |

**Core question:** *Given what's on the books today, how much more will book by each future date, and what do events add on top?*

---

## 2. My AI-Augmented Workflow — How This Got Built

This project was built using an **agentic practitioner** approach: I act as the architect, AI agents handle syntax. Architecture first, code second. Every AI output passes through an audit gate before anything downstream runs.

**Stack for this project:**
- **Claude Code** (CLI) + custom project workspace at `.claude/`
- Two purpose-built agents: **pipeline-architect** (data + forecasting), **business-strategist** (presentation translation)
- One custom skill: **`/reconcile-data`** — reusable data-integrity audit invoked as a gate before any forecast code runs
- **CLAUDE.md** — project constraints file (no ML, modular, explainable) loaded into every agent session

**The 5-step loop I ran for every stage:**

```
SPEC        →  Write business constraints into CLAUDE.md before any code
DECOMPOSE   →  Break problem into independent, testable stages
GENERATE    →  Delegate boilerplate (pandas joins, chart scaffolding) to agent
VERIFY      →  Run /reconcile-data skill — catch hallucinations at the data boundary
COMMIT      →  Only proceed to next stage after audit passes
```

**What each stage looked like in practice:**

🟢 **Step 1: Data Prep & Merge** — agent: `@pipeline-architect`
- Asked: Load + merge OTB and events, apply business logic (dates, join keys, lead time, filter cancellations), output merged dataset
- Got: `1_data_prep.py`, `merged_data.csv` — 28,276 rows; fan-out issue discovered, occupancy outliers flagged, missing event data identified

🟡 **Step 2: Data Quality Audit** — skill: `/reconcile-data`
- Asked: Validate data ("one version of truth"), fix fan-out + outliers + accounting logic, create clean dataset
- Got: `1b_data_patch.py`, `reconciled_data.csv` — 4,732 clean rows; fan-out resolved (1 row per hotel-date), occupancy capped, integrity confirmed

🟠 **Step 3: Forecast Model** — agent: `@pipeline-architect`
- Asked: Build explainable 90-day forecast (no black-box ML), use OTB + Pickup + Event Impact, output forecasts + charts
- Got: `2_forecast_model.py`, `forecast_90days.csv` — 180-row forecast, 3 charts (Occupancy, RevPAR, Pickup), clear pickup + event weighting logic

🔴 **Step 4: Presentation** — agent: `@business-strategist`
- Asked: Translate results into interview-ready presentation with methodology, insights, recommendations
- Got: `PRESENTATION.md` — full narrative + business insights + strategy, ready for screen-share interview

**How I audit AI output (directly answering the JD's cover letter question):**

- I don't verify syntax line-by-line. I test **outputs** against strict business boundaries:
  - Occupancy ∈ [0, 1]
  - `rooms_sold + left_to_sell + ooo == total_rooms` for every row
  - `revenue_sold ≈ rooms_sold × adr_sold` within $1.50 rounding tolerance
  - Event joins must not fan-out (row count in == row count out)
- If any boundary fails, the agent rewrites. If the agent can't explain **why** a number is what it is, the number doesn't ship.

This is the same principle I applied at OMEL AI, where I built a safety layer intercepting enterprise chatbot hallucinations.

---

## 3. The Model — Three Explainable Components

```
Forecast Occupancy  =  OTB Occupancy  +  Pickup Rate  +  Event Weight   (cap 1.0)
Forecast RevPAR     =  Forecast Occupancy  ×  Current ADR

Event Weight        =  min( visitors / rooms / 1000 ,  0.15 )   # 15% ceiling
```

| Component | What it is | Why this choice |
|---|---|---|
| **OTB Occupancy** | Ground truth — already booked | Not a prediction. Auditable. |
| **Pickup Rate** | Expected additional bookings by arrival | **Derived empirically** from 26 OTB snapshots — not an external assumption |
| **Event Weight** | Incremental occ lift from market events | Normalized by room count; capped at +15 pts so a single event can't flip a forecast |

---

## 4. Data Audit — "One Version of the Truth" Before Forecasting

I treat reconciliation as a gate, not an afterthought. The `/reconcile-data` skill ran before any forecasting code executed.

| Check | Finding | Decision |
|---|---|---|
| Naive market+date event join | **4,732 → 28,276 rows** (6× fan-out) | Pre-aggregated events to 841 day-summaries before the join |
| Occupancy outliers | **32 rows > 100%** (Boston Apr 19–21) | Real overbooking signal — capped at 1.0, flagged for Ops |
| Revenue integrity | Max delta **$1.36** vs `rooms × ADR` | Within $1.50 rounding tolerance — accepted |
| Join keys (markets) | 100% overlap, zero orphaned records | Passed |
| Forecast formula | Manual verification on all 180 output rows | Zero residual — formula exactly matches CSV |

The audit **is** the work. A forecast built on unreconciled data is a confident lie.

---

## 5. Pickup Derivation — The Empirical Core

For each (hotel, future date), source data contains ~13 snapshots showing bookings build toward check-in. That lets me measure pickup **empirically** by lead-time bucket — no external curves, no borrowed assumptions.

```python
for each business_date:
    rooms_at_checkin = rooms_sold at lead_time ≈ 0
    for each lead_time bucket (7, 14, 30, 60, 90):
        rooms_at_bucket = rooms_sold at that bucket
        pickup[bucket] = (rooms_at_checkin - rooms_at_bucket) / total_rooms
# average across all business dates → hotel-specific pickup curve
```

![Pickup Curve](charts/chart3_pickup_curve.png)

**Two distinct market personalities emerge:**
- **Boston** — steep curve, **+56.3%** pickup over 90 days → demand builds fast, rate calls must be made early
- **Santa Monica** — shallow curve, **+36.6%** pickup over 90 days → more room for demand stimulation

The curve shape drives the recommendations in §7.

---

## 6. Results — Evidence the Logic Works

![Occupancy Forecast](charts/chart1_occupancy_forecast.png)

![RevPAR Forecast](charts/chart2_revpar_forecast.png)

| | **Hotel A — Santa Monica** | **Hotel B — Boston** |
|---|---|---|
| Avg Occupancy | 62.0% | 88.7% |
| Avg RevPAR | $157.46 | $298.91 |
| Sellout Dates | 0 | 26 of 90 |
| Peak Date | Jul 4 → $237 RevPAR | Sep 17 (Hans Zimmer) → $432 RevPAR |

Every spike ties to a named event in the source data — every number traces back to a row.

---

## 7. Recommendations — Business Translation

### Rec 1 — Boston Rate Fencing · ~$75K incremental
Four sellout dates where ADR already sits at $422 (Sep 9, 16, 17, 26). Forecast confirms the demand ceiling; lift ADR to **$480–$520**. Timeline: 24–48 hours in the PMS.

### Rec 2 — Santa Monica Soft-Window Stimulation · ~$258K–$335K incremental
Aug 4 – Sep 14 runs at **58% occupancy** with a thin event calendar. Pickup curve is steepest 45–60 days out — that's the launch window for leisure and group offers.

### Rec 3 — Overbooking Review · Zero cost
32 source-data rows show negative `left_to_sell` on Boston Apr 19–21. Intentional yield strategy, or a system/process defect? Flag to Ops this week. Either answer improves data integrity.

---

## 8. Limitations — Stated Openly

Honest about what this model is **not**, so the next iteration is obvious:

- **Not** a rate forecast. ADR is held at OTB baseline. Model surfaces *where* to act on rate, not the rate itself.
- **Not** competitor-aware. No comp-set rates in scope.
- **Not** reactive to event cancellations. Requires a rerun. Pipeline is modular — single-date reforecast is trivial.
- **Not** continuous. Built on 26 static snapshots; production would replace with a live OTB feed.

**Next iteration:** competitor rate feed, macro demand signals (flight search, weather), day-of-week seasonality layer, continuous OTB ingest. Natural Tableau dashboard once the pipeline is API-fronted.

---

## 9. Architecture — Built to Scale Across the Portfolio

```
[Load CSVs]  →  [Reconcile / Audit]  →  [Forecast]  →  [Translate]
 1_data_prep      1b_data_patch          2_forecast_model    PRESENTATION.md
                  /reconcile-data
                  skill (gate)
```

- **Modular.** Each stage is a function, not a script.
- **FastAPI-ready.** Functions slot behind REST endpoints with no refactor.
- **Portable.** New hotel = one config entry + rerun. No code change.
- **Dashboard-ready.** Output CSV plugs into Tableau for proactive reporting.

The same architecture works for the Property Data Portal: **inputs → audit gate → transform → output** with AI agents handling the transform logic under a verification boundary. That's the workflow I'd bring on day one.

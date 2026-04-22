---
name: Pebblebrook Forecast Pipeline — Architecture & Key Facts
description: Core pipeline design, data facts, and modeling decisions for the 90-day OTB + event forecast
type: project
---

Pipeline is in two numbered scripts:
- `1_data_prep.py` / `1b_data_patch.py` — OTB + Events reconciliation → `reconciled_data.csv`
- `2_forecast_model.py` — 90-day occupancy & RevPAR forecast → `forecast_90days.csv` + 3 charts

**Key data facts (reconciled_data.csv):**
- 4,732 rows, 19 columns; hotels: hotel_a (315 rooms, Santa Monica CA), hotel_b (238 rooms, Boston MA)
- 26 snapshot_dates from 2025-01-06 → 2025-06-30; business_dates through 2025-09-28
- "Today" (latest snapshot) = 2025-06-30; 90-day window = 2025-07-01 → 2025-09-28
- 180 forecast rows (90 dates × 2 hotels)

**Modeling approach (non-negotiable per CLAUDE.md):**
- Explainable: OTB base + historical pickup rate + event lift multiplier
- No black-box / deep learning models

**Pickup rate findings:**
- hotel_a: 36.6% additional occ at lead_time=90 (picks up ~115 rooms on avg)
- hotel_b: 56.3% additional occ at lead_time=90 (picks up ~134 rooms on avg); much steeper curve

**Event weight formula:**
- visitor_density = total_visitors / total_rooms
- event_weight = min(visitor_density / 1000, 0.15)  [cap at +15% occ lift]
- Most large Boston events hit the 0.15 cap due to very high visitor counts vs 238 rooms

**90-day forecast summary:**
- hotel_a: avg occ 62.0%, avg RevPAR $157.46 (July 4th peak at 96.5%)
- hotel_b: avg occ 88.7%, avg RevPAR $298.91 (many 100% dates driven by events)

**Why:** Business-focused PoC for Pebblebrook; logic must be explainable to non-technical stakeholders.
**How to apply:** When extending the pipeline, preserve the modular function structure and the pickup → event → cap formula sequence.

---
name: Pebblebrook BI Forecast Project
description: 90-day occupancy and RevPAR forecast PoC for Pebblebrook Hotels — two-hotel pilot, interview context
type: project
---

This is a proof-of-concept 90-day forecast pipeline built for a Pebblebrook Hotels interview. The audience is the Senior Director of Operational Excellence and the Manager of Enterprise AI Solutions.

The pipeline covers two hotels: hotel_a (Santa Monica, CA, 315 rooms) and hotel_b (Boston, MA, 238 rooms).

**Why:** Built as a 90-minute interview deliverable. Explainability and auditability matter more than model accuracy. Non-technical stakeholders must be able to trace every number back to source data.

**How to apply:** When generating analysis or presentations for this project, prioritize plain-English explanations before formulas. Always tie findings to specific dates and dollar impacts. The staged pipeline (Load → Validate → Forecast) is a core design principle — reference it when discussing methodology.

Key model parameters:
- hotel_a: 90-day avg occ 62.0%, avg RevPAR $157.46, pickup +36.6% over 90 days
- hotel_b: 90-day avg occ 88.7%, avg RevPAR $298.91, pickup +56.3% over 90 days
- Event weight cap: +15 occupancy points max (visitor_density / 1000, capped at 0.15)
- Fan-out bug caught in validation: naïve join produced 28,276 rows vs correct 4,732 — fixed by pre-aggregating events to 841 event-day summaries
- hotel_b had 32 overbooking outliers (negative left_to_sell Apr 19–21) — capped at 1.0, flagged for ops review

PRESENTATION.md is saved at /Users/yeomyung/Desktop/BI_Project/PRESENTATION.md.

# COCKPIT — Live Interview Reference

Single page. No scrolling. Glance-only.

---

## T-15 MIN PRE-CALL

- [ ] Silence phone. Quit Slack/email/iMessage.
- [ ] Test screen share (record 30 sec self-test, verify audio).
- [ ] Water on desk. Bathroom.
- [ ] Charts folder open in Finder preview.
- [ ] Breathe. Rehearse elevator pitch once out loud.

---

## TAB OPEN ORDER (left → right)

1. Finder — `BI_Project/` folder tree
2. `CLAUDE.md`
3. `charts/chart1_occupancy_forecast.png`
4. `charts/chart2_revpar_forecast.png`
5. `charts/chart3_pickup_curve.png`
6. `1b_data_patch.py` — scroll to `fix_occupancy_outliers` + `aggregate_events`
7. `2_forecast_model.py` — scroll to `build_forecast`
8. `forecast_90days.csv` — Numbers/Excel, sort by business_date
9. `PRESENTATION.md` — **2nd monitor only, never shared**

---

## WALKTHROUGH TIMING (15 min max)

| Clock | Show | Say |
|---|---|---|
| 0:00 | Folder tree | "30 sec on structure. Agentic Practitioner approach — architecture first." |
| 0:30 | CLAUDE.md | "Constraints written before code. Explainable, modular, auditable." |
| 2:00 | chart1 | "Two very different hotels. SM 62%. Boston 88.7%." |
| 4:00 | chart2 | "Jul 4 peak SM $237. Sep 17 Hans Zimmer $432 Boston. Every spike ties to an event." |
| 6:00 | chart3 | "Pickup curve gap. Boston steeper. Boston rate calls need to be early." |
| 8:00 | 1b_data_patch.py | "Fan-out story. 4,732 → 28,276 → 4,732. 32 overbooking rows capped. $1.36 rev tolerance." |
| 11:00 | build_forecast | "Formula: OTB occ + pickup + event weight, capped at 1.0. 15% event cap. One line." |
| 12:00 | PRESENTATION.md (shown briefly) | "Three recs: $75K Boston rate, $258–335K SM stim, zero-cost overbooking review." |
| 14:00 | chart2 | Mic drop. Pause. Invite questions. |

---

## GOLD NUMBERS (memorize cold)

| # | Value |
|---|---|
| 1 | SM avg occ **62.0%**, RevPAR **$157.46** |
| 2 | Boston avg occ **88.7%**, RevPAR **$298.91** |
| 3 | Jul 4 SM peak: **96.5% occ, $237 RevPAR**, 12K visitors |
| 4 | Sep 17 Boston Hans Zimmer: **$432 RevPAR** |
| 5 | Boston sellout dates: **26 of 90** |
| 6 | Pickup 90-day: SM **+36.6%** (+115 rooms), Boston **+56.3%** (+134 rooms) |
| 7 | Event weight cap: **15%** occupancy lift |
| 8 | Fan-out: **4,732 → 28,276 → 4,732** (6× bug pre-empted) |
| 9 | Revenue tolerance: **$1.36** max delta (within $1.50 gate) |
| 10 | Overbooking: **32 rows** (Apr 19–21 Boston), capped at 1.0 |

**Formula:** `Forecast Occ = OTB Occ + Pickup + Event Weight (cap 1.0)` · `Forecast RevPAR = Occ × Current ADR`
**Event weight:** `min(visitors / rooms / 1000, 0.15)`

---

## THREE RECOMMENDATIONS

**1. Boston Rate Fencing** — Target Sept 9, 16, 17, 26 (4 sellouts, avg ADR $422). Lift ADR $422 → $500 = **~$75K incremental**. Timeline: 24–48 hrs in PMS.

**2. Santa Monica Soft-Window Stim** — Aug 4 – Sep 14 (42 days, 58% avg occ). +8–10 occ pts = 1,000–1,300 room nights × $258 ADR = **$258K–$335K incremental**. Launch 45–60 days ahead.

**3. Overbooking Review** — 32 hotel_b rows negative left_to_sell Apr 19–21. Ask Ops: intentional strategy or system error? **Zero cost**. Immediate flag.

---

## Q&A ONE-LINERS (if hit, start here)

- **"How do you audit AI output?"** → "`/reconcile-data` skill. OMEL AI was the same principle — safety layer on AI output. Test boundaries, not syntax."
- **"How would you scale this?"** → "Already modular. FastAPI wrap, Docker, nightly via GitHub Actions, Tableau feed. New hotel = config, not rebuild."
- **"Why not ML?"** → "4,732 rows × 2 hotels = overfit risk. Stakeholders need 'why July 11 at 100%?' auditable. Transparent formula wins."
- **"Confidence in ADR?"** → "ADR pulled from OTB. I forecast occupancy, not rate. Model shows where to act; revenue team decides rate."
- **"What if event cancels?"** → "Rerun with updated data. Pipeline modular, single-date reforecast trivial. Flagged as known limitation."
- **"Validate pickup rates?"** → "Empirical from 26 OTB snapshots. Not assumptions. Recalibrates as snapshots accumulate."
- **"You used AI — can you explain logic?"** → "Syntax by agent. Architecture by me. I specified: explainable model, visitor-density event weights, 15% cap, empirical pickup. Agent wrote pandas. That's the JD."

---

## MIC DROP CLOSE

"Transparent, auditable 90-day forecast. Every number traces to source data. Every stage verified before the next ran. AI as leverage, not autopilot. Architecture first, syntax second. Audit layer on top. Happy to discuss how this operationalizes inside Pebblebrook's BI environment."

**Your question back:** *"What does the first 90 days look like in this role?"*

---

## RULES (do not break)

- Never say "AI planned my workflow." Architecture is **yours**.
- Word "orchestrate" max 2×. More = rehearsed.
- Section 4 (audit) under 3 min. Discipline, not detail.
- Every recommendation → dollar figure.
- Pause after each section. Let them interject.
- Don't skip overbooking rec. Free trust win.

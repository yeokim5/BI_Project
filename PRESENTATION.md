# Pebblebrook Hotels — 90-Day Occupancy & RevPAR Forecast
## Interview Presentation Script
**Presenter:** Revenue Management BI Specialist
**Audience:** Senior Director of Operational Excellence, Manager of Enterprise AI Solutions
**Format:** Screen-share walkthrough — speak naturally through each section

---

## Agenda

1. Methodology & Approach — why we built the model this way
2. Key Findings — what the data is telling us about each hotel
3. Actionable Recommendations — three strategies tied directly to the forecast
4. Data Audit — what we found before we ever ran a model

---

---

## Section 1 — Methodology & Approach

**[Speaker note: Open with the "why" before showing any numbers. This frames everything that follows.]**

Thank you for the time today. I want to start by briefly explaining why I built the model the way I did, because the methodology choice was intentional.

Given the 90-minute constraint, I had two options: I could reach for a sophisticated machine learning approach — gradient boosting, LSTM, something that might squeeze out a few extra accuracy points — or I could build something that every person in this room could audit on the spot. I chose the second path deliberately.

The model is built on three components that map directly to how revenue managers already think:

**Component 1 — On-the-Books (OTB) baseline.** What rooms are already sold, as of the snapshot date. This is the floor. It's real, auditable data from the source system.

**Component 2 — Pickup Rate.** Not every room that will sell has sold yet. Historically, hotels pick up a predictable percentage of their remaining inventory as the arrival date approaches. We calculated that pickup curve from the OTB data itself — no external assumptions required. The numbers are in the data.

**Component 3 — Event Weight.** Events drive incremental demand above what the booking curve would predict on its own. We translate event visitor volume into an occupancy lift using a simple, capped formula I'll walk through in a moment.

The final forecast formula is:

```
Forecast Occupancy = OTB Occupancy + Pickup Rate + Event Weight  (capped at 100%)
Forecast RevPAR    = Forecast Occupancy × Current ADR
```

That's it. Any number we produce can be traced directly back to the source data. If a stakeholder asks "why is Boston forecast at 100% on July 11th?", we can show them exactly which event drove it, exactly what the pickup assumption is, and exactly what ADR we used.

**On the event weight formula specifically** — before I show the math, let me explain it in plain English. We ask a simple question: how many visitors is this event expected to bring, relative to the size of the hotel? A 50,000-person conference landing in a market with 238 rooms is a very different signal than a 500-person corporate seminar. We normalize by room count to capture that difference, and we cap the maximum lift at 15 occupancy points so we never forecast an impossible outcome from a single event. Boston's largest events consistently hit that cap. Santa Monica rarely exceeds a 5-point lift.

The math:

```
visitor_density = total_visitors / total_rooms
event_weight    = min(visitor_density / 1000, 0.15)
```

Finally, the pipeline was built in three stages — Load, Validate, then Forecast. We did not run the model on raw data. I'll come back to what we found in the validation gate in Section 4.

---

---

## Section 2 — Key Findings

**[Speaker note: Tell a story about two very different hotels. Use the numbers to make it concrete. Don't just recite statistics — connect them to business reality.]**

[CHART: 90-Day Forecast Occupancy — hotel_a vs. hotel_b, side by side]

The headline finding is that these two hotels have fundamentally different demand profiles, and the forecast reflects that clearly.

### Hotel A — Santa Monica, CA (315 rooms)

Santa Monica comes in with a 90-day average forecasted occupancy of **62.0%** and an average RevPAR of **$157.46**.

That is a solid leisure market performance, but there are meaningful soft spots in the calendar. Demand is steady but not exceptional. The event calendar generates occasional spikes, but there are no weeks where we're seeing the kind of event density that drives near-sellout conditions.

The one clear highlight is **July 4th** — the Santa Monica 4th of July Parade draws an estimated 12,000 visitors and generates a +3.8% event lift. Our forecast shows **96.5% occupancy and $237 RevPAR** on that date. That is the peak of the 90-day window for this hotel.

The pickup curve for Santa Monica shows demand materializing more gradually — the hotel picks up approximately **36.6% of its remaining rooms** over the 90-day window, with the steepest pickup in the 30-to-60-day lead time range. The implication is that Santa Monica has room to work with, but you need to get demand signals moving well before arrival.

[CHART: Santa Monica Pickup Curve — lead time vs. incremental rooms sold]

### Hotel B — Boston, MA (238 rooms)

Boston tells a very different story.

90-day average occupancy: **88.7%.** Average RevPAR: **$298.91.** That is nearly double Santa Monica on a per-available-room basis.

Boston's calendar from July through September is dense with high-visitor events, and the model reflects that in the forecast. Let me call out three specific dates:

**July 9–12** — the USENIX Annual Technical Symposium overlaps with a Red Sox home series. All four dates reach **100% forecasted occupancy**, with RevPAR ranging from **$300 to $364**. These are effectively sold-out nights.

**September 17** — the World of Hans Zimmer concert. **$432 RevPAR** forecast. Single-event, high-demand spike.

**September 9** — the Future of Passive Housing conference. **$427 RevPAR** forecast. This one is notable because it's a mid-September conference that keeps RevPAR above $420 even as summer demand softens. It tells us the corporate/conference segment is carrying Boston's shoulder season performance.

[CHART: Boston RevPAR by Date — July through September, with event annotations]

The pickup curve for Boston is steeper and faster than Santa Monica. Boston picks up an additional **56.3% of total room inventory** across the 90-day window — that is 134 incremental rooms on top of OTB. The curve shows demand building quickly, which means rate decisions on high-demand dates need to be made early.

| Lead Time | Santa Monica Pickup | Boston Pickup |
|-----------|---------------------|---------------|
| 90 days   | +36.6% (+115 rooms) | +56.3% (+134 rooms) |
| 60 days   | +33.1%              | +52.3% |
| 30 days   | +24.5%              | +39.6% |
| 14 days   | +15.6%              | +22.0% |
| 7 days    | +9.0%               | +11.6% |

The bottom line: Boston is a high-demand market that is forecast to run near capacity for much of this window. The strategic question isn't "how do we fill these rooms?" It's "are we capturing the right rate?"

Santa Monica has the opposite challenge — adequate capacity, moderate demand, and identifiable soft windows where proactive stimulation will pay off.

---

---

## Section 3 — Actionable Recommendations

**[Speaker note: These are the "so what." Each recommendation ties directly to a specific finding. Keep the business logic front and center before getting into the tactic.]**

We have three recommendations. They are ranked by revenue impact and short-term actionability.

---

### Recommendation 1 — Dynamic Rate Fencing on Boston's Sellout Dates

**Target:** Hotel B — September 9 (Passive House conference), September 16, September 17 (Hans Zimmer concert), September 26 — four confirmed sellout dates with ADR averaging $421

**The situation:** Our forecast shows these dates at 100% occupancy with ADR ranging from $405–$432. The current ADR embedded in the forecast is the historical booking average — approximately $420. When a hotel is forecast to sell out, holding lower rate tiers open is leaving revenue on the table.

**The recommendation:** We recommend closing lower rate tiers immediately on these four dates and targeting an ADR in the **$480–$520 range**. The demand signal is there — the event visitor volume, the booking velocity, and the pickup curve all confirm that this market will absorb a rate increase. Guests who book conferences and concerts plan in advance and have demonstrated price tolerance for the convenience of proximity.

**Expected impact:** If we shift ADR from $420 to $500 on four sellout nights across 238 rooms, that is approximately **$76,160 in incremental revenue** from rate alone, with no change in occupancy. Even a partial rate capture in the $460–$480 range generates $38,000–$57,000 in incremental RevPAR.

**Timeline:** This is a quick win. Rate tier changes can be implemented within 24–48 hours in most PMS environments.

---

### Recommendation 2 — Demand Stimulation for Santa Monica's Soft Window

**Target:** Hotel A — August 4 through September 14 (forecast occupancy 52–65%, limited event activity)

**The situation:** Santa Monica's forecast reveals a meaningful soft window in late summer and early fall. This is not a demand crisis — it is a gap between where OTB sits today and what the pickup curve projects. The pickup curve tells us demand materializes slowly for this hotel. If we wait for organic pickup to fill the gap, we lose pricing power in the process.

**The recommendation:** Launch targeted promotions — extended-stay discounts, corporate rate packages, or direct-channel incentives — beginning **45 to 60 days before the soft window** (approximately late June). The 30-to-60-day lead time range is where Santa Monica's pickup curve is steepest. Promotions launched in that window intercept demand at its most price-sensitive and conversion-ready moment.

Specific tactics to evaluate: 3-night minimum stay discounts for the August leisure segment; a direct-book corporate rate for LA-adjacent companies; and coordination with the hotel's sales team on group quotes for dates in the 52–60% forecast range.

**Expected impact:** Recovering 8–10 occupancy points across the 41-day soft window — from a 58% average to a 66–68% average — translates to roughly **1,000–1,300 additional room nights.** At current ADR for Santa Monica (~$258), that represents approximately **$258,000–$335,000 in incremental revenue.**

**Timeline:** Promotion design and channel loading: 2–3 weeks. Campaign execution: 4–6 weeks ahead of the soft window.

---

### Recommendation 3 — Operational Review of Boston's April Overbooking Signal

**Target:** Hotel B — April 19–21 (32 rooms flagged with negative left_to_sell in source data)

**The situation:** During our data validation step, we identified that hotel_b showed negative available rooms on April 19, 20, and 21. That means rooms_sold exceeded total available inventory — a physical impossibility in the data, and a real-world overbooking condition. We capped these values at 1.0 occupancy to preserve model integrity, but the underlying data signal deserves a direct operational response.

**The recommendation:** We recommend the Revenue and Operations teams review the inventory controls on these three dates. Two scenarios are possible. First, this is an intentional overbooking strategy — in which case, walk procedures, compensation policies, and displacement risk calculations should be documented and confirmed. Second, this is a system or human error — in which case, inventory controls need to be tightened to prevent the same condition from recurring on high-demand future dates.

This recommendation costs nothing to investigate and protects the hotel from a guest experience and liability exposure that no revenue strategy can offset.

**Timeline:** Immediate. Flag to the Operations team this week.

---

---

## Section 4 — Data Audit

**[Speaker note: Keep this section efficient — 2–3 minutes max. The goal is to show discipline, not to walk through every check. Lead with the fan-out story because it's the clearest example of "one version of the truth" discipline.]**

Before we ran a single forecast, we ran a reconciliation gate. I want to briefly walk through what we found, because it directly affects confidence in the numbers you just saw.

**Source data:** 4,732 rows of OTB data across 26 snapshot dates and 2 hotels. 7,197 event records spanning January 2024 through September 2025.

**The headline finding in validation:** A naïve join of the two datasets — matching on market and date without pre-aggregating events — produced **28,276 rows instead of 4,732.** That is a 6x fan-out error. In plain terms: the same OTB record was being counted multiple times because multiple events fell on the same date in the same market. A model built on that joined dataset would have systematically overstated event impact on every multi-event date. We caught this before any modeling ran.

The fix was straightforward — pre-aggregate the events dataset down to 841 event-day summaries (one row per market per date), then join. The resulting dataset is clean and 1:1 matched.

**Other findings from the audit:**

- **32 occupancy outliers corrected:** Hotel B showed negative left_to_sell on April 19–21 — the overbooking condition mentioned in Recommendation 3. We capped these at 1.0 occupancy and flagged for operational review.
- **Revenue integrity check passed:** Maximum discrepancy between reported revenue and the rooms_sold × ADR calculation was $1.36. That is consistent with rounding in the source system and is within acceptable tolerance.
- **Join key integrity:** 100% market overlap between OTB and events data. Boston MA and Santa Monica CA matched perfectly with no orphaned records.
- **Cancellations filtered:** All cancelled events were excluded before calculating event weights. No duplicate event IDs were present in the final dataset.

The pipeline handled all of this in the validation stage before any forecast numbers were produced. The model you saw in Section 2 was built on clean, reconciled data.

---

---

## Section 5 — Forward Look & Next Steps

**[Speaker note: End with confidence. This is the "why this matters beyond today" moment.]**

To summarize what we have built:

We have a **transparent, auditable 90-day forecast pipeline** that combines on-the-books data, historical pickup curves, and event-weighted demand signals into a formula that any revenue manager can explain to a general manager — and any finance team can interrogate with confidence.

The model is modular by design. The three stages — Load, Validate, Forecast — are independent functions. Adding a third hotel requires updating the hotel lookup table and re-running the pipeline. Adding a new event category requires adjusting the weight formula in one place. Connecting this to a live PMS feed or a FastAPI endpoint is a natural next step rather than a rebuild.

We are confident in the directional accuracy of these forecasts. We are equally confident about what the model does not do: it does not predict unexpected event cancellations, it does not incorporate competitor rate data, and it does not account for macro demand shifts beyond what the current OTB trend implies. Those are known limitations, not hidden ones.

The recommendations we've laid out — rate fencing on Boston's sellout dates, demand stimulation for Santa Monica's soft window, and the overbooking review — are all actionable within the current operational structure. None of them require the forecast to be perfect to be worth pursuing.

We would welcome the opportunity to discuss how this pipeline could be operationalized within Pebblebrook's broader BI environment — and what the right next iteration looks like in partnership with your teams.

---

## Discussion & Questions

**[Speaker note: Pause here. Invite questions. Anticipated themes are listed below for reference — do not read these aloud.]**

*Anticipated Finance / Operations questions:*

- "How confident are you in the ADR assumption?" — ADR is pulled directly from current OTB. We are not forecasting rate, only occupancy. Rate strategy is a decision for the revenue team; the model surfaces where to act.
- "What happens if an event gets cancelled?" — The model would need to be re-run with updated event data. The modular design makes re-forecasting a single date straightforward. This is a known limitation.
- "Why not use a machine learning model?" — With 4,732 rows across 26 snapshots and 2 hotels, we have limited training data. A transparent formula outperforms an overfit model in this data environment, and it is far more defensible with stakeholders.
- "Can this be automated?" — Yes. The pipeline is written as reusable functions. Scheduling a nightly run against a live data feed is achievable without a major architecture change.
- "How do we validate the pickup rate assumptions?" — The pickup rates were derived from the OTB snapshot history in the source data. As more snapshots accumulate, these rates can be recalibrated. They are not static assumptions — they are empirical measurements from the data itself.

---

*End of presentation script.*

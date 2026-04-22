# Hotel Revenue Management — Domain Dictionary

All terms used in this project, plain English first, formula second.

---

## Core Revenue Metrics

**ADR — Average Daily Rate**
Revenue per room that was actually sold. Not per available room — only sold ones.
`ADR = revenue_sold / rooms_sold`
Example: $25,000 revenue ÷ 100 rooms sold = $250 ADR.
Think of it as: *the average price a guest paid per night.*

**RevPAR — Revenue Per Available Room**
The single most important hotel performance metric. Combines both occupancy AND rate into one number. Finance uses this to compare hotels regardless of size.
`RevPAR = revenue_sold / total_available_rooms`
OR
`RevPAR = Occupancy % × ADR`
Example: 80% occupancy × $250 ADR = $200 RevPAR.
Think of it as: *how much revenue each room generated, whether sold or not.*

Why RevPAR matters: if RevPAR is flat but occupancy rises → rate is dropping (margin erosion). If RevPAR rises but occupancy is flat → pricing power is up (good).

**Occupancy %**
Percentage of available rooms that were sold on a given night.
`Occupancy = rooms_sold / total_rooms`
Example: 190 rooms sold ÷ 238 total rooms = 79.8% occupancy.

---

## Booking & Inventory Terms

**OTB — On The Books**
How many rooms are already booked for a future date, as of right now (or as of a snapshot date). This is committed demand — not a forecast.
Think of it as: *the confirmed reservation count for a future night, measured today.*

**Snapshot Date**
The date the OTB data was captured. A single future date can have many snapshots — one from 90 days out, one from 60 days out, etc. This creates the booking curve.
Example: `snapshot_date = 2025-04-01`, `business_date = 2025-07-04` means "as of April 1st, here's how many rooms were booked for July 4th."

**Business Date**
The actual future night guests will stay. The date the reservation is FOR.

**Lead Time**
Days between snapshot date and business date.
`lead_time = business_date - snapshot_date`
A lead time of 90 means you're looking 90 days in advance.

**Rooms Sold**
Number of rooms with confirmed reservations for a given business date, as of the snapshot date.

**Left to Sell**
Remaining rooms that can still be booked.
`left_to_sell = total_rooms - rooms_sold - ooo`

**OOO — Out of Order**
Rooms physically unavailable: maintenance, renovation, damage. Cannot be sold. Removed from inventory.
`total_rooms = rooms_sold + left_to_sell + ooo`

**Total Rooms**
Fixed hotel capacity. hotel_a = 315 rooms, hotel_b = 238 rooms in this project.

**Overbooking**
Intentionally selling more rooms than physically exist — hotels do this deliberately because some guests always cancel or no-show. When it actually happens (guests show up and no room exists), the hotel "walks" the guest to another hotel at its own expense.
In our data: Boston Apr 19–21 had negative `left_to_sell` = real overbooking, not a data error.

---

## Forecasting Terms

**Pickup**
Additional rooms that will be booked between now and the actual stay date. The difference between current OTB and expected final demand.
`pickup = expected_final_rooms - current_rooms_sold`
Think of it as: *how many more reservations will come in before check-in day.*

**Pickup Rate**
Pickup expressed as a percentage of total rooms, by lead time bucket.
`pickup_rate = (rooms_at_checkin - rooms_at_lead_time) / total_rooms`
In this project: Boston pickup rate at 90-day lead = +56.3% (steeper, faster-building market). Santa Monica = +36.6% (slower, leisure market).

**Booking Curve / Booking Pace**
The shape of how reservations accumulate over time toward a stay date. A steep curve = demand builds fast (conference/urban markets like Boston). A shallow curve = demand builds slowly (leisure markets like Santa Monica). The curve is derived from stacking multiple snapshots of the same future date.

**Event Weight / Event Lift**
The incremental occupancy boost from a nearby event (concert, conference, sports). Calculated as:
```
visitor_density = total_visitors / total_rooms
event_weight = min(visitor_density / 1000, 0.15)
```
Cap at +15 occupancy points. Example: 12,000 visitors ÷ 315 rooms ÷ 1000 = 0.038 = +3.8% lift.
Why cap at 15%? A single event can't physically fill more than 15 extra points of a hotel — after that, the constraint is rate, not volume.

**Fan-out**
A data bug where joining two tables produces more rows than expected, because one side has multiple matches. In this project: OTB had 4,732 rows. After naive join with events (multiple events per date), it exploded to 28,276 rows — each OTB row duplicated once per event on that date. Fix: pre-aggregate events to one row per market-date before joining.

**Forecast Formula (this project)**
```
Forecast Occupancy = OTB Occupancy + Pickup Rate + Event Weight  (capped at 1.0)
Forecast RevPAR    = Forecast Occupancy × Current ADR
```

---

## Revenue Management Strategy Terms

**Rate Fencing**
Setting different prices for different customer segments or booking windows. "Fence" high-demand dates behind higher rates to capture willingness-to-pay. Example: raise ADR from $422 → $480 on Boston sellout dates.

**Yield Management**
The practice of adjusting price and inventory based on demand signals to maximize revenue. Core idea: sell the right room to the right customer at the right price at the right time.

**Dynamic Pricing**
Automatically adjusting rates in real time based on demand, competitor rates, and events. The output of this forecast informs dynamic pricing decisions.

**Sellout Date**
A date where occupancy reaches (or is forecast to reach) 100%. At sellout, the only revenue lever is rate — you can't sell more rooms than exist.

**Rate Ceiling / Rate Cap**
The maximum price the market will bear for a room on a given night before guests shift to competitors. Identifying the ceiling is a key use of this forecast.

**Soft Window / Soft Period**
Dates with weak demand and low forecast occupancy. Where demand stimulation tactics (discounts, promotions, group offers) have the highest ROI. In this project: Santa Monica Aug 4 – Sep 14 at 52–65% occupancy.

**Shoulder Dates**
Days surrounding peak demand (before and after a sellout event). Often underpriced. Example: days adjacent to a Boston conference cluster.

**Walk (verb)**
When a hotel is overbooked and a guest must be sent to another property. The original hotel pays for the guest's room elsewhere + compensation. Walking a guest = cost + reputational risk.

**PMS — Property Management System**
The hotel's core software that manages reservations, room assignments, rates, and billing. Where rate changes are implemented. "24–48 hours to implement in PMS" means how fast a rate decision can go live.

---

## Data Quality Terms

**Accounting Integrity Check**
Verifying the room math balances: `rooms_sold + ooo + left_to_sell = total_rooms`. If this doesn't hold for every row, data is corrupt.

**Revenue Integrity Check**
Verifying: `revenue_sold ≈ rooms_sold × adr_sold` within rounding tolerance. In this project: max delta was $1.36, within the $1.50 tolerance — passed.

**Join Key**
The column(s) used to link two datasets. In this project: `location` (OTB) matched to `market` (events). 100% overlap = clean join, no orphaned records.

**One Version of the Truth**
Principle that all downstream analysis (forecasts, reports, dashboards) must trace to a single, reconciled, agreed-upon dataset. Not two people running different numbers from different sources.

---

## Market Terms

**Market**
A geographic demand zone — the city/area where the hotel competes. In this project: "Boston, MA" and "Santa Monica, CA". Events impact demand across the market, not just one hotel.

**Influence Radius**
How far an event's demand impact spreads geographically. A small local event affects a 1-mile radius. A major conference affects the entire metro market.

**Comp Set / Competitive Set**
The peer hotels a property benchmarks against for pricing. Not in this project's data — called out as a known limitation.

**Market Mix**
The blend of demand sources: leisure travelers, corporate travelers, group bookings, OTA (online travel agency) bookings. Affects both ADR and booking pace.

---

## Quick Reference — Formula Sheet

| Metric | Formula |
|--------|---------|
| ADR | `revenue_sold / rooms_sold` |
| RevPAR | `revenue_sold / total_rooms` = `Occupancy × ADR` |
| Occupancy | `rooms_sold / total_rooms` |
| Left to Sell | `total_rooms - rooms_sold - ooo` |
| Lead Time | `business_date - snapshot_date` |
| Pickup Rate | `(rooms_at_checkin - rooms_at_lead_time) / total_rooms` |
| Event Weight | `min(total_visitors / total_rooms / 1000, 0.15)` |
| Forecast Occ | `OTB_occ + pickup_rate + event_weight` (cap 1.0) |
| Forecast RevPAR | `forecast_occ × current_ADR` |

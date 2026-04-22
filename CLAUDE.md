# Pebblebrook BI Forecast Pipeline PoC

This project is a proof-of-concept (PoC) automated pipeline that combines OTB data and Events data to forecast Occupancy and RevPAR for the next 90 days.

## Architecture & Execution Rules
1. **Agentic Practitioner Approach:** No autopilot. Code must be modular — split into [Data Load] -> [Validation] -> [Forecast] stages. Each stage requires user audit before proceeding.
2. **One Version of the Truth:** Data integrity is the top priority. When merging data from two systems (CSVs), verify no conflicts or missing records exist.
3. **Scalable & Modular:** All Python code must be reusable functions — not one-off scripts. Build for easy integration into Pebblebrook's internal systems or a FastAPI environment.
4. **Business Focused:** Avoid complex black-box models (e.g., deep learning). Use explainable, practical logic — time-series base multiplied by event weights — understandable to non-technical stakeholders.

BI Project

Prompt: You have been tasked to help build a 90-day occupancy and revenue forecast for a hotel. Using the provided datasets and leveraging other technology as you see fit, develop said forecast and be prepared to present your methodology, findings and recommendations. We would ask that you don't spend more than 90 minutes on this project. Please note, there are no right/wrong answers; we are interested in seeing your logic and approach, rather than a perfect, production-ready model, and your ability to present your findings. There is no formal deliverable required, simply be prepared to share your screen and walk us through your scratchpad, code, or spreadsheet logic.

 

Data Sets: There are two datasets to assist with the development of the forecast:

 

data-otb.csv: This data set includes current occupancy and revenue data that is on the books

·                hotel_code: Unique Identifier for the hotel

·                snapshot_date: The date in which the 'on the books' data was as of

·                business_date: The future date that the data is tied to

·                rooms_sold: The number of rooms that have currently been sold

·                adr_sold: Average Daily Rate (Revenue/Rooms Sold) of the sold rooms

·                revenue_sold: Amount of revenue booked for the date

·                ooo: The number of rooms that are currently out of order

·                left_to_sell: The number of remaining rooms available to be sold

·                occupancy: Rooms Sold / Total Rooms

·                revpar: Revenue Sold / Total Available Rooms

·                location: Market of the hotel

 

data-events.csv: The data set includes markets' events spanning from the Jan 2024 to Sep 2025

·                event_id : Unique Identifier for the event

·                market: Market of the event

·                event_date: Date of the event

·                name: Name of the event

·                category: Event category

·                location: Venue for the Event (if applicable)

·                visitors: Estimated number of visitors for the event

·                influence_radius: The area of the market impacted by the event

·                lat: Latitude of the event

·                lon: Longitude of the event

·                labels: Additional descriptors of the event

·                is_cancelled: Whether the event is 


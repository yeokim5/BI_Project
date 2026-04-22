🟢 Prompt 1: Data Preparation & Merging
이 프롬프트는 90일 OTB 예측의 핵심 논리(Lead time, Event mapping)를 AI에게 강제하여 베이스 코드를 짜게 합니다.

text
We are starting the 90-minute BI forecasting project based on the instructions in `BI_Project_Description.txt`.

Please invoke `@pipeline-architect` to write and execute a modular Python script (`1_data_prep.py`) that loads and merges `data-otb.csv` and `data-events.csv` from the `PEB_BI_Project_Data` folder.

Follow this business logic for the merge:
1. Parse date columns correctly (snapshot_date, business_date, event_date).
2. The primary key for joining is the hotel's `location` (from OTB) and the event's `market`.
3. Join events to OTB data where the `event_date` matches the `business_date`.
4. Calculate the "Lead Time" (the difference between `business_date` and `snapshot_date`).
5. Ensure we filter out cancelled events (`is_cancelled`).

Write the code to output a merged dataset (`merged_data.csv`). Run the script using the bash tool and report back with a summary of the merged dataframe (rows, columns, and any missing data). Do not build the forecast model yet.

🟢 Prompt 1: Result
created : 1_data_prep.py, merged_data.csv
⏺ Pipeline complete. Key findings:

  merged_data.csv — 28,276 rows x 24 cols

  Watch before forecasting:
  1. Fan-out: 4,732 OTB rows → 28,276 after join. Multiple events per (location, date) expand rows. Need to aggregate events per date (sum visitors, count events)
  before modeling.
  2. 302 occupancy outliers outside [0,1] — likely ooo denominator issue. Use rooms_sold / (rooms_sold + left_to_sell) as safer target.
  3. No cancelled events in source data — filter in place, works if future data has them.
  4. 5.7% null on event cols — expected, OTB dates with no events (left join).

  Ready for Phase 2: EDA or event aggregation + feature engineering. Which first?


🟡 Prompt 2: Data Quality Audit (Validation)
AI가 만든 데이터가 "One version of the truth"인지 점검하는 핵심 단계입니다. 면접관에게 당신의 QA 역량을 어필하는 부분입니다.
That's exactly why we don't blindly model data! The Fan-out issue (multiple events per date) and the 302 occupancy outliers are critical. We need "one version of    
  the truth" before forecasting.                                                                                                                                       
                                                                                                                                                                       
  Please run the /reconcile-data skill on merged_data.csv to perform the full business logic checks.                                                                   
  Specifically, verify and fix:                                                                                                                                        
                                                                                                                                                                       
  Fan-out Fix: Aggregate the event data (e.g., sum of visitors, count of events) so we have exactly ONE row per hotel per date.                                        
                                                                                                                                                                       
  Accounting Integrity & Outliers: Does rooms_sold + ooo + left_to_sell consistently equal total rooms? Fix the 302 occupancy outliers using your suggested safe       
  target rooms_sold / (rooms_sold + left_to_sell).                                                                                                                     
                                                                                                                                                                       
  Does revenue_sold match rooms_sold * adr_sold?                                                                                                                       
                                                                                                                                                                       
  Are there any unmatched markets between the events and OTB datasets?                                                                                                 
                                                                                                                                                                       
  Write a quick patch script (1b_data_patch.py) to fix these discrepancies, run it, and output a clean reconciled_data.csv. Report the findings clearly so I can       
  interviewers. 

🟡 Prompt 2: Result
---                                                                                                                                                                  
  Data Integrity Report                                                                                                                                                
                       
  ┌──────────────────┬───────────┬──────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐    
  │      Check       │  Status   │  Affected    │                                                      Notes                                                      │    
  │                  │           │     Rows     │                                                                                                                 │
  ├──────────────────┼───────────┼──────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤    
  │ Schema / Types   │ ✅        │ 0            │ All required columns present, dates parsed                                                                      │  
  ├──────────────────┼───────────┼──────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤    
  │ Accounting Check │ ✅        │ 0            │ rooms_sold + ooo + left_to_sell = total_rooms within ±1 on all rows                                             │    
  ├──────────────────┼───────────┼──────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤    
  │ Join Key Match   │ ✅        │ 0            │ Both markets match 100%: Boston, MA & Santa Monica, CA                                                          │    
  ├──────────────────┼───────────┼──────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤  
  │ Events Quality   │ ✅        │ 0            │ No cancellations, no duplicate IDs, no null visitors                                                            │    
  ├──────────────────┼───────────┼──────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤  
  │ Occupancy Range  │ ✅        │ 32           │ hotel_b oversold dates April 19–21 — left_to_sell went negative. Capped at 1.0. Root cause: real overbooking,   │    
  │                  │ (fixed)   │              │ not data error.                                                                                                 │  
  ├──────────────────┼───────────┼──────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤    
  │ Revenue          │ ✅        │ 0            │ Max delta $1.36 — rounding in source system, within $1.50 tolerance                                             │  
  │ Integrity        │           │              │                                                                                                                 │
  ├──────────────────┼───────────┼──────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤    
  │ Fan-out          │ ✅        │ —            │ 7,197 event rows → 841 aggregated event-day summaries                                                           │
  │                  │ (fixed)   │              │                                                                                                                 │    
  └──────────────────┴───────────┴──────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  
                                                                                                                                                                       
  Executive Summary (for interviewers)                                                                                                                                 
  
  What we found: Three issues, none fatal.                                                                                                                             
                                                            
  1. Fan-out — joining OTB to events directly multiplied rows because multiple events happen on the same date. Fixed by aggregating events first (sum visitors, count  
  events) before joining — now exactly 1 row per (hotel × snapshot × business_date).
  2. Oversold dates — hotel_b sold more than its 238 rooms on ~3 dates in April 2025 (real overbooking, not bad data). Occupancy capped at 1.0 for model safety; these 
  dates are flagged.                                                                                                                                                   
  3. OTB is a booking curve, not a point-in-time snapshot — 26 snapshot dates × 266 future dates = 4,732 rows. The same future date appears up to 13 times as bookings
  build up. This is the correct structure for pickup / booking curve modeling.                                                                                         
                                                            
  reconciled_data.csv — 4,732 rows × 19 cols. Zero nulls in forecast columns. Zero true PK duplicates.                                                                 
                                                            
  Proceed to Phase 3?                                                                                                                                                  
                                                            
  Data is clean. Ready for forecast modeling. Approve to advance?        

  지금 상황은 면접 준비에 있어 **가장 완벽한 모범 답안(Textbook example)을 도출한 상태**입니다. 

AI가 작성한 저 요약본(Executive Summary)은 실제 호텔 Revenue Manager들이 매일 다루는 OTB(On The Books) 데이터의 핵심적인 특징과 오류를 정확히 짚어냈습니다. 면접에서 이 내용을 어떻게 100% 이해(Full comprehension)하고 브리핑(Present)할 수 있는지, 완벽한 "방어 논리와 대본"을 짜드립니다.

***

### 🧠 1. 결과에 대한 완벽한 이해 (Full Comprehension)

면접관(Matthew Klein)은 데이터의 특성을 얼마나 이해하고 있는지를 볼 것입니다. AI가 찾아낸 3가지 이슈가 호텔 비즈니스에서 어떤 의미인지 아셔야 합니다.

**① Fan-out (데이터 뻥튀기) 해결**
* **의미:** 원본 데이터는 특정 호텔의 특정 날짜(예: 4월 20일)에 대한 줄이 1개여야 합니다. 그런데 그날 주변에 '음악 축제'와 'IT 컨퍼런스'가 동시에 열리면, 조인(Join) 과정에서 호텔 데이터가 2줄로 복제됩니다. 
* **왜 중요한가:** 이대로 모델을 돌리면 호텔 방이 2배로 부풀려져서 수익이 2배로 계산됩니다.
* **어떻게 해결했나:** AI에게 지시하여 이벤트 데이터를 먼저 합산(sum visitors, count events)하여 1줄로 만든 다음 호텔 데이터에 붙이도록 수정했습니다.

**② Occupancy Range (점유율 이상치) 해결**
* **의미:** 점유율은 공식상 `(판매된 객실 / 전체 객실)`이므로 최대 1.0(100%)이어야 합니다. 그런데 32개 행에서 1.0을 초과했습니다.
* **왜 중요한가:** 호텔업계에서는 비행기처럼 **'오버부킹(Overbooking)'**을 고의로 받습니다(노쇼 대비). 즉, 이건 데이터 오류가 아니라 실제 일어나는 비즈니스 현상입니다. 하지만 예측 모델에 1.2(120%) 같은 값이 들어가면 모델이 망가집니다.
* **어떻게 해결했나:** AI에게 지시하여 모델 안전성을 위해 점유율의 최댓값을 1.0으로 강제 고정(Cap)시켰습니다.

**③ OTB는 '스냅샷'의 누적 (Booking Curve)**
* **의미:** 똑같은 미래의 숙박일(business_date)에 대해 데이터가 여러 개 있습니다. 왜냐하면 한 달 전, 보름 전, 일주일 전에 각각 데이터를 뽑은 '스냅샷(snapshot_date)'이 누적되어 있기 때문입니다.
* **왜 중요한가:** 이게 바로 90일 예측의 핵심인 **'예약 속도(Booking Pace/Pickup)'**를 계산하는 재료가 됩니다. 

***

### 🎙️ 2. 면접 프레젠테이션 대본 (How to present)

면접 시 화면에 이 "Data Integrity Report"를 띄워놓고 이렇게 브리핑하세요. (영어 대본)

> **"Before jumping into the forecast model, I want to highlight the Data Reconciliation phase. I strictly ran an audit skill because raw joins often break business logic in hotel data. As you can see on the screen, the system successfully caught and fixed three critical issues:**
>
> **First, the Fan-out issue.** When joining the OTB data with the Events data, the row count exploded from 4,700 to over 28,000. This happens when multiple events occur on the same day in the same market. If left unfixed, this would have artificially multiplied our rooms and RevPAR. I instructed the agent to aggregate the event metrics—like summing the total visitors—before the join, ensuring exactly one row per hotel per date.
>
> **Second, the Occupancy Outliers.** The audit caught 32 rows where occupancy exceeded 100%. While I understand that intentional overbooking is a standard revenue management practice to offset cancellations, leaving these values above 1.0 would mathematically skew the time-series forecast. So, I applied a strict 1.0 cap for modeling safety.
> 
> **Finally, the OTB Data Structure.** The audit verified that the OTB data represents a booking curve with multiple snapshot dates for the same business date. This confirmed that my approach—using the historical 'pickup' pace combined with event weight—is the correct methodology for this dataset.
>
> **Because of this strict verification step, I can confidently say our baseline data represents 'one version of the truth'. We are now ready to generate the 90-day forecast."**

***

### 🚀 3. 다음 스텝 (Phase 3 진행)

이제 데이터가 완벽하게 준비되었습니다. 망설이지 마시고 바로 3번째 프롬프트를 복사해서 붙여넣으세요!

**[대화창에 입력할 프롬프트 - Phase 3]**
> "Yes, approve to advance. The data is validated and clean. 
> Now, invoke `@pipeline-architect` to build the 90-day forecast model in a new script (`2_forecast_model.py`). 
>
> Modeling Constraints & Approach:
> 1. Avoid black-box deep learning. Use a highly explainable approach.
> 2. Forecast Formula Concept: Forecasted Final Demand = Current OTB (rooms_sold) + Expected Pickup (calculated from the historical booking curve lead times) + Event Impact Weight (based on aggregated visitors).
> 3. Generate a 90-day future forecast for both Occupancy % and RevPAR.
>
> Run the script, output `forecast_90days.csv`, and save 2-3 presentation-ready PNG charts showing the 90-day forecast, explicitly highlighting dates where major events drive RevPAR spikes. Summarize the pickup and event weight logic." 

🟠 Prompt 3: 90-Day Forecasting & Visualization
가장 중요한 90일 예측 단계입니다. 복잡한 딥러닝을 쓰지 않고, 면접에서 설명하기 쉬운(Explainable) 논리적 모델을 강제합니다.
Yes, approve to advance. The data is validated and clean. 

Now, invoke `@pipeline-architect` to build the 90-day forecast model in a new script (`2_forecast_model.py`) using `reconciled_data.csv`.

Modeling Constraints & Approach:
1. Avoid black-box deep learning. Use a highly explainable, practical approach (e.g., calculating historical pickup rates based on lead time, then applying multipliers based on event `visitors`).
2. Forecast Formula Concept: Final Forecast = Current OTB + Expected Pickup + (Event Impact Weight).
3. Target Metrics: Generate a 90-day future forecast for both `Occupancy %` and `RevPAR`.

Outputs needed:
1. Run the script and generate 2-3 clean, presentation-ready PNG charts showing the 90-day Occupancy and RevPAR forecast, clearly highlighting the dates where major events cause spikes.
2. Save the final forecast to `forecast_90days.csv`.

Summarize exactly how you calculated the "Expected Pickup" and the "Event Impact Weight" so I can easily explain the underlying math and logic to the interviewers.

🟠 Prompt 3: Result
                                                                 
⏺ All 3 charts clean and presentation-ready. Pipeline complete.                                                                                                        
                                                                                                                                                                       
  ---                                                               
  Status: Phase 3 done. All outputs verified:                                                                                                                          
                                                                                                                                                                       
  - forecast_90days.csv — 180 rows (90 days × 2 hotels), 17 columns, zero nulls                                                                                        
  - All 3 charts render correctly                                                                                                                                      
                                                                                                                                                                       
  Quick math summary for interviewers:                                                                                                                                 
                                                                                                                                                                       
  Expected Pickup = average rooms gained historically between current lead time and arrival day, expressed as % of total rooms. hotel_b picks up 56% of its rooms in   
  the final 90 days vs hotel_a's 37% — Boston demand builds faster and later.
                                                                                                                                                                       
  Event Impact Weight = min(total_visitors / total_rooms / 1000, 0.15). Scales visitor volume relative to hotel size, capped at +15% occupancy lift. Real example: 4th 
  of July parade Santa Monica = 12,000 visitors / 315 rooms / 1000 = +3.8% lift. Boston conference with 2.4M visitors hits the 15% cap.
                                                                                                                                                                       
  Final formula: forecast_occ = current_occ + pickup_rate + event_weight (capped at 1.0)                                                                               
   
  Key story for presentation:                                                                                                                                          
  - hotel_b (Boston) forecasts 88.7% avg occupancy, $299 RevPAR — events calendar is dense and high-visitor
  - hotel_a (Santa Monica) forecasts 62.0% avg occupancy, $157 RevPAR — softer demand, fewer major events                                                              
  - July 4th weekend + July conference cluster = peak revenue windows for both properties                
                                                                                                                                                                       
  Ready for presentation. Want EDA charts (Phase 2 visualizations) or proceed straight to the interview deck narrative?      

🔴 Prompt 4: Presentation Script & Strategy (Final)
AI가 도출한 숫자와 차트를, 면접관(경영진)이 듣고 싶어 하는 비즈니스 인사이트로 번역합니다.
Excellent. The forecast and charts are ready. 
Now, invoke `@business-strategist` to prepare my final deliverable: `PRESENTATION.md`.

This presentation is what I will use to walk the interviewers through my logic via screen share. 

Please structure the markdown file as follows:
1. **Methodology & Approach**: Explain why we chose a transparent "OTB + Pickup + Event Weight" model instead of a black-box ML model, highlighting our focus on practical business logic under a 90-minute constraint.
2. **Key Findings**: Summarize the 90-day forecast using the specific numbers generated (e.g., Boston $299 RevPAR vs Santa Monica $157 RevPAR, the 15% event cap, booking curve differences). Explicitly point out how specific events are driving RevPAR compressions on specific dates like July 4th.
3. **Actionable Recommendations**: Based on the forecast, provide 3 concrete revenue optimization strategies (e.g., "Yield management: Raise ADR on date X due to Event Y" or "Launch promotions for dates A-B to fill remaining `left_to_sell`").
4. **Data Audit**: Briefly mention how we actively decomposed the task and audited the data for Fan-out/Outliers using the `/reconcile-data` skill before modeling.

Write the script in a professional, confident "Speaker Notes" tone so I can naturally read/reference it during my interview with the Senior Director of Operational Excellence and the Manager of Enterprise AI Solutions.

🔴 Prompt 4: Result

                                                     
  Project deliverables done:                                                                                                                                           
  
  ┌───────────────────────────────────────────┬───────────────────────────┐                                                                                            
  │                   File                    │          Status           │                                                                                          
  ├───────────────────────────────────────────┼───────────────────────────┤                                                                                            
  │ 1_data_prep.py + merged_data.csv          │ Load + join               │                                                                                            
  ├───────────────────────────────────────────┼───────────────────────────┤
  │ 1b_data_patch.py + reconciled_data.csv    │ Validated, fan-out fixed  │                                                                                            
  ├───────────────────────────────────────────┼───────────────────────────┤                                                                                            
  │ 2_forecast_model.py + forecast_90days.csv │ 180-row forecast          │                                                                                            
  ├───────────────────────────────────────────┼───────────────────────────┤                                                                                            
  │ charts/chart1_occupancy_forecast.png      │ Occ by hotel              │                                                                                          
  ├───────────────────────────────────────────┼───────────────────────────┤                                                                                            
  │ charts/chart2_revpar_forecast.png         │ RevPAR with event labels  │                                                                                          
  ├───────────────────────────────────────────┼───────────────────────────┤                                                                                            
  │ charts/chart3_pickup_curve.png            │ Booking curve methodology │                                                                                          
  ├───────────────────────────────────────────┼───────────────────────────┤                                                                                            
  │ PRESENTATION.md                           │ Interview script          │
  └───────────────────────────────────────────┴───────────────────────────┘

  Tips for screen share:                                                                                                                                               
  - Open PRESENTATION.md + charts folder side-by-side
  - Section 4 (Data Audit) → open 1b_data_patch.py to show the reconcile code live                                                                                     
  - Section 2 → switch to chart2_revpar_forecast.png when citing Boston $432 RevPAR
  - Anticipate the "why not ML?" question — answer is in the Q&A section, memorize it                                                                                  
                                                                                                                                                                       
  Good luck.                                                                                                                                                           
                             
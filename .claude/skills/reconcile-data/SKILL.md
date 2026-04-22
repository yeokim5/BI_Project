---
name: reconcile-data
description: Validates "One version of the truth" before merging OTB and Events datasets. Use whenever user mentions data validation, join integrity, data merging, rooms_sold errors, market matching, occupancy anomalies, left_to_sell discrepancy, data reconciliation, or any data quality check. Required gate before entering forecast modeling (Phase 3+).
---

# Data Reconciliation Skill

You are a data architect and QA engineer. Before advancing to the forecast model, execute the validation steps below **in order** and report results. Write each step as an independent, reusable function (FastAPI-compatible).

---

## Validation Steps

### Step 1: Schema & Type Validation
```python
def validate_schema(df_otb, df_events):
    # Parse date columns
    for col in ['snapshot_date', 'business_date']:
        df_otb[col] = pd.to_datetime(df_otb[col])
    df_events['event_date'] = pd.to_datetime(df_events['event_date'])

    # Assert required columns exist
    required_otb = ['hotel_code', 'snapshot_date', 'business_date',
                    'rooms_sold', 'ooo', 'left_to_sell', 'occupancy', 'revpar', 'location']
    required_events = ['event_id', 'market', 'event_date', 'visitors',
                       'influence_radius', 'is_cancelled']
    # Return list of missing columns per dataset
```

### Step 2: Total Rooms Derivation & Accounting Check
Key formula: `total_rooms = rooms_sold / occupancy` (rows where occupancy > 0 only)

```python
def validate_accounting(df_otb):
    df = df_otb[df_otb['occupancy'] > 0].copy()
    df['total_rooms_derived'] = (df['rooms_sold'] / df['occupancy']).round()
    df['accounting_sum'] = df['rooms_sold'] + df['ooo'] + df['left_to_sell']
    df['discrepancy'] = (df['accounting_sum'] - df['total_rooms_derived']).abs()

    # Tolerance: ±1 (allow rounding error)
    bad_rows = df[df['discrepancy'] > 1]
    # Return bad_rows with hotel_code, business_date, discrepancy columns
```

**Business impact:** Accounting mismatch corrupts `rooms_available` → RevPAR forecast is wrong.

### Step 3: Join Key Integrity (Most Critical)
OTB `location` ↔ Events `market` is the join key.

```python
def validate_join_keys(df_otb, df_events):
    otb_markets = set(df_otb['location'].str.strip().unique())
    event_markets = set(df_events['market'].str.strip().unique())

    unmatched_hotels = otb_markets - event_markets   # hotels with no event data
    unmatched_events = event_markets - otb_markets   # events with no hotel
    overlap = otb_markets & event_markets

    # Return: overlap count/ratio, both unmatched lists
```

**Business impact:** Unmatched markets get event weight = 0. Confirm this is intentional.

### Step 4: Events Data Quality
```python
def validate_events(df_events):
    cancelled_count = df_events['is_cancelled'].sum()
    duplicate_events = df_events[df_events.duplicated(['event_id', 'event_date'])]
    null_visitors = df_events['visitors'].isna().sum()
    zero_radius = (df_events['influence_radius'] <= 0).sum()
    date_range = (df_events['event_date'].min(), df_events['event_date'].max())
    # Return summary dict
```

### Step 5: Occupancy Range Check
```python
def validate_occupancy(df_otb):
    out_of_range = df_otb[(df_otb['occupancy'] < 0) | (df_otb['occupancy'] > 1)]
    edge_cases = df_otb[df_otb['occupancy'].isin([0.0, 1.0])]  # flag separately
```

---

## Output Format

After all checks, report using this exact structure:

```
## Data Integrity Report

| Check             | Status  | Affected Rows | Notes                        |
|-------------------|---------|---------------|------------------------------|
| Schema / Types    | ✅ / ❌ | N             | ...                          |
| Accounting Check  | ✅ / ❌ | N             | hotel_code × date list       |
| Join Key Match    | ✅ / ⚠️ | N             | Unmatched markets list       |
| Events Quality    | ✅ / ⚠️ | N             | Cancelled: N, Duplicates: N  |
| Occupancy Range   | ✅ / ❌ | N             | ...                          |

### Executive Summary (non-technical language)
[Issue found → Root cause → Recommended action: Drop / Impute / Manual review]

### Proceed to Phase 3?
Issues above have been reviewed. Approve to advance to forecast modeling?
```

---

## Discrepancy Resolution Rules

| Issue Type              | Default Action                  | User Confirmation Required |
|-------------------------|---------------------------------|---------------------------|
| Accounting error ≤ 1    | Ignore (rounding tolerance)     | No                        |
| Accounting error > 1    | Flag and hold                   | **Yes**                   |
| Unmatched join key      | Event weight = 0 for that market| Yes (confirm intent)      |
| is_cancelled = True     | Auto filter out                 | No                        |
| Occupancy out of range  | Exclude row, report             | **Yes**                   |
| Duplicate event_id×date | Keep first row                  | Yes                       |

**Principle:** Auto-fix only what is unambiguous. When in doubt, surface to user for judgment.

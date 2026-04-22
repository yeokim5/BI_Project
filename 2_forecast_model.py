"""
2_forecast_model.py
-------------------
Pebblebrook BI Forecast Pipeline — 90-Day Occupancy & RevPAR Forecast

Architecture:
    [Load] -> [Current OTB] -> [Pickup Rates] -> [Event Weights]
             -> [Forecast] -> [Save] -> [Charts]

Approach: Explainable time-series pickup + event multiplier.
No black-box models. All math is auditable.

Working directory: /Users/yeomyung/Desktop/BI_Project/
Input:  reconciled_data.csv
Output: forecast_90days.csv
        charts/chart1_occupancy_forecast.png
        charts/chart2_revpar_forecast.png
        charts/chart3_pickup_curve.png
"""

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = "/Users/yeomyung/Desktop/BI_Project"
INPUT_FILE = os.path.join(BASE_DIR, "reconciled_data.csv")
OUTPUT_CSV = os.path.join(BASE_DIR, "forecast_90days.csv")
CHARTS_DIR = os.path.join(BASE_DIR, "charts")

# Lead-time buckets used for pickup curve aggregation (days until arrival)
LEAD_TIME_BUCKETS = [0, 7, 14, 21, 30, 45, 60, 90]

# Event weight cap: each 1,000 visitors per room of supply = +0.1% occ; cap at +15%
VISITORS_PER_1000_WEIGHT = 0.001   # 1 visitor-per-room unit = 0.001 occ lift
EVENT_WEIGHT_CAP = 0.15            # max occupancy lift from events

sns.set_style("whitegrid")
os.makedirs(CHARTS_DIR, exist_ok=True)


# ===========================================================================
# MODULE 1 — Data Load
# ===========================================================================

def load_data(path: str) -> pd.DataFrame:
    """
    Load reconciled_data.csv, parse date columns, and return a clean DataFrame.

    Returns
    -------
    pd.DataFrame with snapshot_date and business_date as datetime64.
    """
    print(f"[Load] Reading {path}")
    df = pd.read_csv(path)
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
    df["business_date"] = pd.to_datetime(df["business_date"])
    df["has_event"] = df["has_event"].astype(bool)
    print(f"[Load] Loaded {len(df):,} rows | hotels: {sorted(df['hotel_code'].unique())}")
    print(f"[Load] snapshot_date range: {df['snapshot_date'].min().date()} → {df['snapshot_date'].max().date()}")
    print(f"[Load] business_date range: {df['business_date'].min().date()} → {df['business_date'].max().date()}")
    return df


# ===========================================================================
# MODULE 2 — Current OTB Position
# ===========================================================================

def get_current_otb(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each (hotel_code, business_date), extract the row with the
    LATEST snapshot_date. This is the current on-books position.

    Returns
    -------
    pd.DataFrame — one row per (hotel_code, business_date).
    Columns include: current_rooms_sold, current_occupancy, current_adr,
                     current_lead_time, total_rooms, event fields.
    """
    print("\n[OTB] Extracting current on-books position (latest snapshot per date)...")
    idx = df.groupby(["hotel_code", "business_date"])["snapshot_date"].idxmax()
    otb = df.loc[idx].copy().reset_index(drop=True)

    otb = otb.rename(columns={
        "rooms_sold":    "current_rooms_sold",
        "occupancy":     "current_occupancy",
        "adr_sold":      "current_adr",
        "revpar":        "current_revpar",
        "revenue_sold":  "current_revenue",
        "lead_time":     "current_lead_time",
    })

    print(f"[OTB] {len(otb):,} rows (unique hotel × business_date combinations)")
    for hotel, grp in otb.groupby("hotel_code"):
        print(f"[OTB]   {hotel}: {len(grp)} dates, "
              f"avg current occ = {grp['current_occupancy'].mean():.1%}, "
              f"avg lead time = {grp['current_lead_time'].mean():.1f} days")
    return otb


# ===========================================================================
# MODULE 3 — Historical Pickup Rates
# ===========================================================================

def compute_pickup_rates(df: pd.DataFrame) -> dict:
    """
    For each hotel, compute the average ADDITIONAL rooms picked up
    between a given lead_time and lead_time=0 (check-in).

    Method
    ------
    1. For each (hotel, business_date), find rooms_sold at lead_time=0
       (or the closest snapshot to lead_time=0).
    2. For each lead_time bucket, compute:
           additional_rooms = rooms_at_checkin - rooms_at_lead_time
    3. Average across all business_dates.
    4. Express as a fraction of total_rooms → pickup_rate.

    Returns
    -------
    dict: {hotel_code: {lead_time: pickup_rate_fraction}}
        pickup_rate_fraction > 0 means that many more rooms (as % of total)
        are expected to be picked up between now and arrival.
    """
    print("\n[Pickup] Computing historical pickup rates by lead time...")
    rates = {}

    for hotel, hotel_df in df.groupby("hotel_code"):
        total_rooms = hotel_df["total_rooms"].iloc[0]
        pickup_by_lead = {lt: [] for lt in LEAD_TIME_BUCKETS}

        for bdate, date_df in hotel_df.groupby("business_date"):
            date_df = date_df.sort_values("lead_time")

            # Find rooms at check-in (lead_time == 0 or nearest to 0)
            checkin_row = date_df.loc[date_df["lead_time"].idxmin()]
            if checkin_row["lead_time"] > 5:
                # No near-checkin snapshot available — skip this date
                continue
            rooms_at_checkin = checkin_row["rooms_sold"]

            # For each lead_time bucket, find the closest actual snapshot
            for bucket_lt in LEAD_TIME_BUCKETS:
                if bucket_lt == 0:
                    pickup_by_lead[0].append(0.0)
                    continue
                # Find snapshot closest to this bucket without going below it
                available = date_df[date_df["lead_time"] >= bucket_lt]
                if available.empty:
                    available = date_df
                closest = available.loc[(available["lead_time"] - bucket_lt).abs().idxmin()]
                rooms_at_bucket = closest["rooms_sold"]

                additional = rooms_at_checkin - rooms_at_bucket
                # Clip at 0 (can't pick up negative rooms conceptually,
                # though late cancellations can create negatives — we floor at 0)
                additional = max(additional, 0)
                pickup_by_lead[bucket_lt].append(additional / total_rooms)

        # Summarize pickup rates for this hotel
        hotel_rates = {}
        print(f"\n[Pickup] {hotel} (total_rooms={total_rooms}):")
        print(f"{'Lead Time':>12} | {'Dates Used':>10} | {'Avg Add. Rooms':>15} | {'Pickup Rate':>12}")
        print("-" * 58)
        for lt in LEAD_TIME_BUCKETS:
            vals = pickup_by_lead[lt]
            if vals:
                rate = float(np.mean(vals))
                avg_rooms = rate * total_rooms
                print(f"{lt:>12} | {len(vals):>10} | {avg_rooms:>15.1f} | {rate:>11.1%}")
            else:
                rate = 0.0
                print(f"{lt:>12} | {'N/A':>10} | {'N/A':>15} | {'N/A':>12}")
            hotel_rates[lt] = rate

        rates[hotel] = hotel_rates

    return rates


# ===========================================================================
# MODULE 4 — Event Impact Weights
# ===========================================================================

def compute_event_weights(otb: pd.DataFrame) -> pd.DataFrame:
    """
    For each row in the current OTB, compute an event_weight that
    represents additional occupancy lift driven by events.

    Formula
    -------
        visitor_density = total_visitors / total_rooms
        event_weight    = min(visitor_density / 1000, EVENT_WEIGHT_CAP)

    Intuition: For every 1,000 event visitors per available room,
               occupancy lift is capped at EVENT_WEIGHT_CAP (15%).

    Returns
    -------
    pd.DataFrame — otb with added column 'event_weight'.
    """
    print("\n[Events] Computing event weights...")

    otb = otb.copy()
    otb["visitor_density"] = otb["total_visitors"] / otb["total_rooms"]

    # Event weight: only applied to dates WITH events
    otb["event_weight"] = 0.0
    event_mask = otb["has_event"] == True
    otb.loc[event_mask, "event_weight"] = (
        otb.loc[event_mask, "visitor_density"] / 1000
    ).clip(upper=EVENT_WEIGHT_CAP)

    event_rows = otb[event_mask]
    print(f"[Events] {event_mask.sum()} dates have events out of {len(otb)} total")
    print(f"[Events] visitor_density stats (event dates):")
    density_stats = event_rows["visitor_density"].describe()
    for stat in ["min", "25%", "50%", "75%", "max"]:
        print(f"          {stat:>5}: {density_stats[stat]:,.1f} visitors per room")
    print(f"[Events] event_weight range: "
          f"{event_rows['event_weight'].min():.4f} – {event_rows['event_weight'].max():.4f}")

    # Show a few real examples
    print("\n[Events] Sample event weight calculations:")
    sample = event_rows.nlargest(5, "total_visitors")[
        ["hotel_code", "business_date", "total_visitors", "total_rooms",
         "visitor_density", "event_weight", "event_names"]
    ]
    print(sample.to_string(index=False))

    return otb


# ===========================================================================
# MODULE 5 — Interpolate Pickup Rate for Arbitrary Lead Time
# ===========================================================================

def interpolate_pickup_rate(lead_time: float, hotel_rates: dict) -> float:
    """
    Given a lead_time (days), linearly interpolate the pickup_rate
    from the nearest bracket entries in hotel_rates.

    Parameters
    ----------
    lead_time   : int/float — current days until arrival
    hotel_rates : dict      — {lead_time_bucket: pickup_rate_fraction}

    Returns
    -------
    float — expected additional occupancy fraction to be picked up.
    """
    buckets = sorted(hotel_rates.keys())
    if lead_time <= 0:
        return 0.0
    if lead_time >= buckets[-1]:
        return hotel_rates[buckets[-1]]

    # Find surrounding buckets
    lower_lt = max(b for b in buckets if b <= lead_time)
    upper_lt = min(b for b in buckets if b >= lead_time)

    if lower_lt == upper_lt:
        return hotel_rates[lower_lt]

    # Linear interpolation
    lower_rate = hotel_rates[lower_lt]
    upper_rate = hotel_rates[upper_lt]
    frac = (lead_time - lower_lt) / (upper_lt - lower_lt)
    return lower_rate + frac * (upper_rate - lower_rate)


# ===========================================================================
# MODULE 6 — Build Forecast
# ===========================================================================

def build_forecast(
    otb: pd.DataFrame,
    pickup_rates: dict,
    today: pd.Timestamp,
) -> pd.DataFrame:
    """
    Assemble the 90-day forward forecast for each hotel.

    Steps per row
    -------------
    1. current_occupancy      = rooms_sold / total_rooms (already in OTB)
    2. pickup_rate            = interpolate from historical rates at current lead_time
    3. event_weight           = precomputed in otb['event_weight']
    4. forecast_occupancy     = min(current + pickup + event_weight, 1.0)
    5. forecast_rooms         = forecast_occupancy * total_rooms
    6. forecast_adr           = current_adr (OTB ADR as baseline)
    7. forecast_revpar        = forecast_occupancy * forecast_adr

    Only business_dates in (today, today+90] are included.

    Returns
    -------
    pd.DataFrame — forecast with one row per (hotel, business_date).
    """
    print(f"\n[Forecast] Building 90-day forecast from {today.date()} "
          f"to {(today + pd.Timedelta(days=90)).date()}...")

    window_start = today + pd.Timedelta(days=1)
    window_end   = today + pd.Timedelta(days=90)

    forecast_rows = otb[
        (otb["business_date"] >= window_start) &
        (otb["business_date"] <= window_end)
    ].copy()

    print(f"[Forecast] {len(forecast_rows)} (hotel × date) combinations in window")

    # Compute pickup_rate for each row via interpolation
    forecast_rows["pickup_rate"] = forecast_rows.apply(
        lambda row: interpolate_pickup_rate(
            row["current_lead_time"],
            pickup_rates[row["hotel_code"]]
        ),
        axis=1,
    )

    # Assemble final forecast
    forecast_rows["forecast_occupancy"] = (
        forecast_rows["current_occupancy"]
        + forecast_rows["pickup_rate"]
        + forecast_rows["event_weight"]
    ).clip(upper=1.0)

    forecast_rows["forecast_rooms"] = (
        forecast_rows["forecast_occupancy"] * forecast_rows["total_rooms"]
    ).round(1)

    forecast_rows["forecast_adr"] = forecast_rows["current_adr"]

    forecast_rows["forecast_revpar"] = (
        forecast_rows["forecast_occupancy"] * forecast_rows["forecast_adr"]
    ).round(2)

    # Summary
    print("\n[Forecast] Summary by hotel:")
    for hotel, grp in forecast_rows.groupby("hotel_code"):
        print(f"  {hotel}: "
              f"avg occ = {grp['forecast_occupancy'].mean():.1%}  "
              f"avg RevPAR = ${grp['forecast_revpar'].mean():.2f}  "
              f"avg pickup applied = {grp['pickup_rate'].mean():.1%}  "
              f"avg event lift = {grp['event_weight'].mean():.2%}")

    return forecast_rows


# ===========================================================================
# MODULE 7 — Save Forecast
# ===========================================================================

def save_forecast(forecast: pd.DataFrame, path: str) -> None:
    """
    Save the forecast DataFrame to CSV with key columns in logical order.

    Output columns
    --------------
    hotel_code, business_date, total_rooms,
    current_rooms_sold, current_occupancy, current_adr,
    current_lead_time, pickup_rate, event_weight,
    forecast_occupancy, forecast_rooms, forecast_adr, forecast_revpar,
    has_event, event_count, total_visitors, event_names
    """
    print(f"\n[Save] Writing forecast to {path}")

    cols = [
        "hotel_code", "business_date", "total_rooms",
        "current_rooms_sold", "current_occupancy", "current_adr",
        "current_lead_time", "pickup_rate", "event_weight",
        "forecast_occupancy", "forecast_rooms", "forecast_adr", "forecast_revpar",
        "has_event", "event_count", "total_visitors", "event_names",
    ]
    # Only include columns that exist
    cols = [c for c in cols if c in forecast.columns]

    out = forecast[cols].sort_values(["hotel_code", "business_date"])
    out.to_csv(path, index=False)
    print(f"[Save] Saved {len(out):,} rows × {len(cols)} columns")


# ===========================================================================
# MODULE 8 — Reporting
# ===========================================================================

def print_report(forecast: pd.DataFrame) -> None:
    """
    Print the requested reporting tables to stdout.
    """
    print("\n" + "=" * 70)
    print("FORECAST REPORT")
    print("=" * 70)

    for hotel, grp in forecast.groupby("hotel_code"):
        grp = grp.sort_values("business_date")
        hotel_label = hotel.upper()

        # --- Overall averages ---
        avg_occ = grp["forecast_occupancy"].mean()
        avg_revpar = grp["forecast_revpar"].mean()
        print(f"\n{'─'*60}")
        print(f" {hotel_label} — 90-Day Summary")
        print(f"{'─'*60}")
        print(f"  Avg Forecast Occupancy : {avg_occ:.1%}")
        print(f"  Avg Forecast RevPAR    : ${avg_revpar:.2f}")

        # --- Top-5 occupancy dates ---
        top_occ = grp.nlargest(5, "forecast_occupancy")[
            ["business_date", "forecast_occupancy", "forecast_rooms",
             "pickup_rate", "event_weight", "has_event", "event_names"]
        ]
        print(f"\n  Top-5 Highest Forecast Occupancy Dates:")
        print(f"  {'Date':>12} | {'Occ %':>7} | {'Rooms':>6} | "
              f"{'Pickup':>8} | {'Event+':>7} | Event Names")
        print(f"  {'-'*90}")
        for _, r in top_occ.iterrows():
            enames = str(r["event_names"])[:45] if pd.notna(r["event_names"]) else "—"
            print(f"  {str(r['business_date'].date()):>12} | "
                  f"{r['forecast_occupancy']:>7.1%} | "
                  f"{r['forecast_rooms']:>6.0f} | "
                  f"{r['pickup_rate']:>8.1%} | "
                  f"{r['event_weight']:>7.2%} | {enames}")

        # --- Top-5 RevPAR dates ---
        top_revpar = grp.nlargest(5, "forecast_revpar")[
            ["business_date", "forecast_revpar", "forecast_occupancy",
             "forecast_adr", "has_event", "event_names"]
        ]
        print(f"\n  Top-5 Highest Forecast RevPAR Dates:")
        print(f"  {'Date':>12} | {'RevPAR':>8} | {'Occ %':>7} | "
              f"{'ADR':>8} | Event Names")
        print(f"  {'-'*70}")
        for _, r in top_revpar.iterrows():
            enames = str(r["event_names"])[:40] if pd.notna(r["event_names"]) else "—"
            print(f"  {str(r['business_date'].date()):>12} | "
                  f"${r['forecast_revpar']:>7.2f} | "
                  f"{r['forecast_occupancy']:>7.1%} | "
                  f"${r['forecast_adr']:>7.2f} | {enames}")

    # --- Event weight math sample ---
    print(f"\n{'─'*60}")
    print(" EVENT WEIGHT MATH — Real Examples")
    print(f"{'─'*60}")
    print(f"  Formula: visitor_density = total_visitors / total_rooms")
    print(f"           event_weight = min(visitor_density / 1000, {EVENT_WEIGHT_CAP})")
    event_sample = forecast[forecast["has_event"] == True].nlargest(5, "total_visitors")[
        ["hotel_code", "business_date", "total_visitors", "total_rooms",
         "visitor_density", "event_weight"]
    ]
    if "visitor_density" in event_sample.columns:
        print(f"\n  {'Hotel':>8} | {'Date':>12} | {'Visitors':>12} | "
              f"{'Rooms':>6} | {'Density':>8} | {'Weight':>8}")
        print(f"  {'-'*65}")
        for _, r in event_sample.iterrows():
            density = r["total_visitors"] / r["total_rooms"]
            print(f"  {r['hotel_code']:>8} | {str(r['business_date'].date()):>12} | "
                  f"{r['total_visitors']:>12,.0f} | "
                  f"{r['total_rooms']:>6.0f} | "
                  f"{density:>8.1f} | "
                  f"{r['event_weight']:>8.4f}")


# ===========================================================================
# MODULE 9 — Charts
# ===========================================================================

def plot_occupancy_forecast(forecast: pd.DataFrame, charts_dir: str) -> None:
    """
    Chart 1: 90-day occupancy forecast per hotel (2 subplots).
    Event dates overlaid as scatter markers sized by total_visitors.
    """
    print("\n[Charts] Generating Chart 1 — Occupancy Forecast...")
    hotels = sorted(forecast["hotel_code"].unique())

    fig, axes = plt.subplots(len(hotels), 1, figsize=(14, 12), sharex=False)
    if len(hotels) == 1:
        axes = [axes]

    colors = {"hotel_a": "#2563EB", "hotel_b": "#7C3AED"}
    event_color = "#EF4444"

    for ax, hotel in zip(axes, hotels):
        grp = forecast[forecast["hotel_code"] == hotel].sort_values("business_date")
        location = grp["location"].iloc[0] if "location" in grp.columns else hotel

        # Main occupancy line
        ax.plot(
            grp["business_date"],
            grp["forecast_occupancy"] * 100,
            color=colors.get(hotel, "#1f77b4"),
            linewidth=2.2,
            label="Forecast Occupancy",
            zorder=3,
        )

        # Fill under the line
        ax.fill_between(
            grp["business_date"],
            grp["forecast_occupancy"] * 100,
            alpha=0.12,
            color=colors.get(hotel, "#1f77b4"),
        )

        # Event scatter overlay
        event_grp = grp[grp["has_event"] == True]
        if not event_grp.empty:
            # Normalize visitor size for scatter
            max_visitors = event_grp["total_visitors"].clip(lower=1).max()
            sizes = ((event_grp["total_visitors"] / max_visitors) * 200 + 30).clip(30, 350)
            sc = ax.scatter(
                event_grp["business_date"],
                event_grp["forecast_occupancy"] * 100,
                s=sizes,
                color=event_color,
                zorder=5,
                alpha=0.85,
                label="Event Date (size ∝ visitors)",
                edgecolors="white",
                linewidths=0.6,
            )

        ax.set_title(
            f"{hotel.upper()} — {location} | 90-Day Occupancy Forecast",
            fontsize=16, fontweight="bold", pad=12
        )
        ax.set_ylabel("Occupancy (%)", fontsize=12)
        ax.set_ylim(0, 110)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0f}%"))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=0, interval=2))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=10)
        ax.tick_params(axis="y", labelsize=10)
        ax.legend(fontsize=10, loc="upper left")
        ax.grid(True, alpha=0.4)
        ax.axhline(y=100, color="black", linewidth=0.7, linestyle="--", alpha=0.4)

        # Annotate max occ date
        max_row = grp.loc[grp["forecast_occupancy"].idxmax()]
        ax.annotate(
            f"Peak: {max_row['forecast_occupancy']:.1%}\n{max_row['business_date'].strftime('%b %d')}",
            xy=(max_row["business_date"], max_row["forecast_occupancy"] * 100),
            xytext=(10, -30), textcoords="offset points",
            fontsize=9, color=colors.get(hotel, "black"),
            arrowprops=dict(arrowstyle="->", color=colors.get(hotel, "black"), lw=1.2),
        )

    fig.suptitle(
        "Pebblebrook Hotels — 90-Day Occupancy Forecast\n"
        "Methodology: OTB + Historical Pickup + Event Lift",
        fontsize=14, fontweight="bold", y=1.01
    )
    plt.tight_layout()
    out_path = os.path.join(charts_dir, "chart1_occupancy_forecast.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[Charts] Saved: {out_path}")


def plot_revpar_forecast(forecast: pd.DataFrame, charts_dir: str) -> None:
    """
    Chart 2: 90-day RevPAR forecast per hotel (2 subplots).
    Annotate top-3 RevPAR dates with event names.
    """
    print("\n[Charts] Generating Chart 2 — RevPAR Forecast...")
    hotels = sorted(forecast["hotel_code"].unique())

    fig, axes = plt.subplots(len(hotels), 1, figsize=(14, 12), sharex=False)
    if len(hotels) == 1:
        axes = [axes]

    colors = {"hotel_a": "#059669", "hotel_b": "#D97706"}
    event_color = "#EF4444"

    for ax, hotel in zip(axes, hotels):
        grp = forecast[forecast["hotel_code"] == hotel].sort_values("business_date")
        location = grp["location"].iloc[0] if "location" in grp.columns else hotel

        # Main RevPAR line
        ax.plot(
            grp["business_date"],
            grp["forecast_revpar"],
            color=colors.get(hotel, "#1f77b4"),
            linewidth=2.2,
            label="Forecast RevPAR",
            zorder=3,
        )
        ax.fill_between(
            grp["business_date"],
            grp["forecast_revpar"],
            alpha=0.12,
            color=colors.get(hotel, "#1f77b4"),
        )

        # Event scatter overlay
        event_grp = grp[grp["has_event"] == True]
        if not event_grp.empty:
            max_visitors = event_grp["total_visitors"].clip(lower=1).max()
            sizes = ((event_grp["total_visitors"] / max_visitors) * 200 + 30).clip(30, 350)
            ax.scatter(
                event_grp["business_date"],
                event_grp["forecast_revpar"],
                s=sizes,
                color=event_color,
                zorder=5,
                alpha=0.85,
                label="Event Date (size ∝ visitors)",
                edgecolors="white",
                linewidths=0.6,
            )

        # Annotate top-3 RevPAR dates
        top3 = grp.nlargest(3, "forecast_revpar")
        for _, row in top3.iterrows():
            ename = str(row.get("event_names", ""))
            if pd.isna(ename) or ename == "nan":
                ename = "—"
            label = ename[:28] + "…" if len(ename) > 28 else ename
            ax.annotate(
                f"${row['forecast_revpar']:.0f}\n{label}",
                xy=(row["business_date"], row["forecast_revpar"]),
                xytext=(0, 14), textcoords="offset points",
                fontsize=8, ha="center", color="#111827",
                arrowprops=dict(arrowstyle="->", color="#6B7280", lw=1.0),
            )

        ax.set_title(
            f"{hotel.upper()} — {location} | 90-Day RevPAR Forecast",
            fontsize=16, fontweight="bold", pad=12
        )
        ax.set_ylabel("RevPAR ($)", fontsize=12)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"${y:,.0f}"))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=0, interval=2))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=10)
        ax.tick_params(axis="y", labelsize=10)
        ax.legend(fontsize=10, loc="upper left")
        ax.grid(True, alpha=0.4)

    fig.suptitle(
        "Pebblebrook Hotels — 90-Day RevPAR Forecast\n"
        "Methodology: OTB + Historical Pickup + Event Lift",
        fontsize=14, fontweight="bold", y=1.01
    )
    plt.tight_layout()
    out_path = os.path.join(charts_dir, "chart2_revpar_forecast.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[Charts] Saved: {out_path}")


def plot_pickup_curve(df: pd.DataFrame, pickup_rates: dict, charts_dir: str) -> None:
    """
    Chart 3: Historical pickup curve per hotel.
    X-axis: days until arrival (90 → 0, reversed).
    Y-axis: avg rooms on books at that lead time (% of total rooms).
    Also overlays raw data scatter with confidence band.
    """
    print("\n[Charts] Generating Chart 3 — Pickup Curves...")
    hotels = sorted(pickup_rates.keys())

    fig, axes = plt.subplots(1, len(hotels), figsize=(14, 8))
    if len(hotels) == 1:
        axes = [axes]

    colors_main = {"hotel_a": "#2563EB", "hotel_b": "#7C3AED"}
    colors_raw  = {"hotel_a": "#93C5FD", "hotel_b": "#C4B5FD"}

    for ax, hotel in zip(axes, hotels):
        hotel_df = df[df["hotel_code"] == hotel].copy()
        total_rooms = hotel_df["total_rooms"].iloc[0]
        location = hotel_df["location"].iloc[0] if "location" in hotel_df.columns else hotel

        # Build aggregated pickup curve: avg rooms_sold by lead_time across ALL dates
        avg_by_lt = (
            hotel_df.groupby("lead_time")["rooms_sold"]
            .agg(["mean", "std", "count"])
            .reset_index()
        )
        avg_by_lt["mean_pct"] = avg_by_lt["mean"] / total_rooms * 100
        avg_by_lt["std_pct"]  = avg_by_lt["std"]  / total_rooms * 100

        # Scatter raw data (lightly)
        raw_sample = hotel_df.sample(min(len(hotel_df), 800), random_state=42)
        ax.scatter(
            raw_sample["lead_time"],
            raw_sample["rooms_sold"] / total_rooms * 100,
            alpha=0.12,
            s=12,
            color=colors_raw.get(hotel, "#93C5FD"),
            label="Raw observations",
        )

        # Mean line
        ax.plot(
            avg_by_lt["lead_time"],
            avg_by_lt["mean_pct"],
            color=colors_main.get(hotel, "#2563EB"),
            linewidth=2.5,
            label="Avg rooms on books",
            zorder=4,
        )

        # ±1 std band
        ax.fill_between(
            avg_by_lt["lead_time"],
            (avg_by_lt["mean_pct"] - avg_by_lt["std_pct"]).clip(lower=0),
            (avg_by_lt["mean_pct"] + avg_by_lt["std_pct"]).clip(upper=100),
            alpha=0.20,
            color=colors_main.get(hotel, "#2563EB"),
            label="±1 std dev",
        )

        # Overlay pickup_rate buckets as annotated points
        rates = pickup_rates[hotel]
        # Compute avg rooms at lead_time=0 to show absolute position
        avg_at_zero = avg_by_lt.loc[avg_by_lt["lead_time"] == 0, "mean_pct"]
        base_pct = float(avg_at_zero.iloc[0]) if not avg_at_zero.empty else 0.0

        for lt in LEAD_TIME_BUCKETS:
            if lt == 0:
                continue
            rate_pct = rates[lt] * 100  # additional pickup as % of total rooms
            # Y position = avg_at_bucket (from aggregated data)
            bucket_pct_series = avg_by_lt.loc[avg_by_lt["lead_time"] == lt, "mean_pct"]
            if bucket_pct_series.empty:
                continue
            bucket_pct = float(bucket_pct_series.iloc[0])
            ax.annotate(
                f"+{rate_pct:.1f}%",
                xy=(lt, bucket_pct),
                xytext=(0, 10), textcoords="offset points",
                fontsize=8.5, ha="center",
                color=colors_main.get(hotel, "#2563EB"),
                fontweight="bold",
            )
            ax.scatter(lt, bucket_pct, s=80, color=colors_main.get(hotel, "#2563EB"),
                       zorder=5, marker="D")

        ax.set_xlim(92, -2)  # reversed: high lead_time on left = far from arrival
        ax.set_ylim(0, 105)
        ax.set_xlabel("Days Until Arrival (Lead Time)", fontsize=12)
        ax.set_ylabel("Avg Rooms On Books (% of Total)", fontsize=12)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0f}%"))
        ax.set_title(
            f"{hotel.upper()} — {location}\nHistorical Pickup Curve",
            fontsize=14, fontweight="bold", pad=12
        )
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.4)
        ax.tick_params(labelsize=10)

        # Arrow annotation explaining direction
        ax.annotate(
            "← Booking builds as arrival approaches",
            xy=(45, 5), fontsize=9, color="#6B7280", fontstyle="italic",
        )

    fig.suptitle(
        "Historical Pickup Curve — How Bookings Build Toward Arrival\n"
        "Annotations show avg additional rooms expected to be picked up (as % of total rooms)",
        fontsize=13, fontweight="bold", y=1.01,
    )
    plt.tight_layout()
    out_path = os.path.join(charts_dir, "chart3_pickup_curve.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[Charts] Saved: {out_path}")


# ===========================================================================
# PIPELINE ORCHESTRATOR
# ===========================================================================

def run_pipeline() -> None:
    """
    Execute the full 90-day forecast pipeline end-to-end.

    Stages:
        1. Load data
        2. Extract current OTB position
        3. Compute historical pickup rates
        4. Compute event weights
        5. Build forecast
        6. Save forecast CSV
        7. Generate charts
        8. Print report
    """
    print("=" * 70)
    print("PEBBLEBROOK BI FORECAST PIPELINE — 90-DAY OCCUPANCY & REVPAR")
    print("=" * 70)

    # --- Stage 1: Load ---
    df = load_data(INPUT_FILE)

    # Determine "today" = latest snapshot date
    today = df["snapshot_date"].max()
    print(f"\n[Pipeline] Today (latest snapshot): {today.date()}")
    print(f"[Pipeline] Forecast window: {(today + pd.Timedelta(days=1)).date()} "
          f"→ {(today + pd.Timedelta(days=90)).date()}")

    # --- Stage 2: Current OTB ---
    otb = get_current_otb(df)

    # --- Stage 3: Pickup Rates ---
    pickup_rates = compute_pickup_rates(df)

    # --- Stage 4: Event Weights ---
    otb = compute_event_weights(otb)

    # Keep visitor_density in otb for reporting
    if "visitor_density" not in otb.columns:
        otb["visitor_density"] = otb["total_visitors"] / otb["total_rooms"]

    # --- Stage 5: Build Forecast ---
    forecast = build_forecast(otb, pickup_rates, today)

    # --- Stage 6: Save ---
    save_forecast(forecast, OUTPUT_CSV)

    # --- Stage 7: Charts ---
    plot_occupancy_forecast(forecast, CHARTS_DIR)
    plot_revpar_forecast(forecast, CHARTS_DIR)
    plot_pickup_curve(df, pickup_rates, CHARTS_DIR)

    # --- Stage 8: Report ---
    print_report(forecast)

    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    print(f"  Forecast CSV : {OUTPUT_CSV}")
    print(f"  Chart 1      : {os.path.join(CHARTS_DIR, 'chart1_occupancy_forecast.png')}")
    print(f"  Chart 2      : {os.path.join(CHARTS_DIR, 'chart2_revpar_forecast.png')}")
    print(f"  Chart 3      : {os.path.join(CHARTS_DIR, 'chart3_pickup_curve.png')}")


if __name__ == "__main__":
    run_pipeline()

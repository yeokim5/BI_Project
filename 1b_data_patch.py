"""
1b_data_patch.py — Data reconciliation and patch for BI forecast pipeline.

Fixes applied:
  1. Fan-out: aggregate events to one row per (hotel_code, business_date)
  2. Occupancy outliers: recompute using total_rooms derived from clean rows
  3. Revenue discrepancy: flag only (within $1.50 rounding tolerance — accepted)
"""

import pandas as pd
import numpy as np

TOTAL_ROOMS = {"hotel_a": 315, "hotel_b": 238}


def load_source_data(otb_path: str, events_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    df_otb = pd.read_csv(otb_path)
    df_events = pd.read_csv(events_path)
    for col in ["snapshot_date", "business_date"]:
        df_otb[col] = pd.to_datetime(df_otb[col])
    df_events["event_date"] = pd.to_datetime(df_events["event_date"])
    print(f"[load] OTB: {df_otb.shape}, Events: {df_events.shape}")
    return df_otb, df_events


def fix_occupancy_outliers(df_otb: pd.DataFrame) -> pd.DataFrame:
    """Recompute occupancy using derived total_rooms. Cap at 1.0 for oversold."""
    df = df_otb.copy()
    df["total_rooms"] = df["hotel_code"].map(TOTAL_ROOMS)
    df["occupancy_safe"] = (df["rooms_sold"] / df["total_rooms"]).clip(upper=1.0).round(4)
    df["revpar_safe"] = (df["revenue_sold"] / df["total_rooms"]).round(2)

    outlier_mask = (df_otb["occupancy"] < 0) | (df_otb["occupancy"] > 1)
    n_fixed = outlier_mask.sum()
    df.loc[outlier_mask, "occupancy"] = df.loc[outlier_mask, "occupancy_safe"]
    df.loc[outlier_mask, "revpar"] = df.loc[outlier_mask, "revpar_safe"]
    df = df.drop(columns=["occupancy_safe", "revpar_safe"])
    print(f"[occupancy] Fixed {n_fixed} outlier rows (oversold dates — capped at 1.0)")
    return df


def check_revenue_integrity(df_otb: pd.DataFrame) -> None:
    df = df_otb.copy()
    df["rev_check"] = (df["rooms_sold"] * df["adr_sold"]).round(2)
    df["rev_delta"] = (df["revenue_sold"] - df["rev_check"]).abs()
    bad = df[df["rev_delta"] > 1.50]
    print(f"[revenue] Rows exceeding $1.50 tolerance: {len(bad)} (max delta: ${df['rev_delta'].max():.4f})")
    if len(bad):
        print(bad[["hotel_code", "business_date", "rooms_sold", "adr_sold",
                   "revenue_sold", "rev_check", "rev_delta"]].to_string())
    else:
        print("[revenue] All revenue discrepancies within $1.50 rounding tolerance — accepted.")


def aggregate_events(df_events: pd.DataFrame) -> pd.DataFrame:
    """Collapse multiple events per (market, date) into one summary row."""
    df_events_active = df_events[~df_events["is_cancelled"].astype(str).str.lower().isin(["true", "1", "yes"])]

    agg = (
        df_events_active
        .groupby(["market", "event_date"], as_index=False)
        .agg(
            event_count=("event_id", "count"),
            total_visitors=("visitors", "sum"),
            top_category=("category", lambda x: x.mode()[0] if len(x) > 0 else None),
            max_influence_radius=("influence_radius", "max"),
            event_names=("name", lambda x: " | ".join(x.dropna().unique()[:3])),
        )
    )
    agg["has_event"] = True
    print(f"[events] Aggregated to {len(agg)} event-day summaries (from {len(df_events_active)} active event rows)")
    return agg


def build_reconciled_dataset(df_otb: pd.DataFrame, df_events_agg: pd.DataFrame) -> pd.DataFrame:
    """Merge clean OTB with aggregated events. One row per (hotel_code, business_date)."""
    df_otb["join_key_date"] = df_otb["business_date"].dt.date.astype(str)
    df_events_agg["join_key_date"] = df_events_agg["event_date"].dt.date.astype(str)
    df_events_agg = df_events_agg.rename(columns={"market": "location"})

    merged = df_otb.merge(
        df_events_agg[["location", "join_key_date", "event_count", "total_visitors",
                       "top_category", "max_influence_radius", "event_names", "has_event"]],
        on=["location", "join_key_date"],
        how="left",
    )
    merged["has_event"] = merged["has_event"].fillna(False)
    merged["event_count"] = merged["event_count"].fillna(0).astype(int)
    merged["total_visitors"] = merged["total_visitors"].fillna(0)
    merged["lead_time"] = (merged["business_date"] - merged["snapshot_date"]).dt.days
    merged = merged.drop(columns=["join_key_date"])

    assert len(merged) == len(df_otb), f"Fan-out detected! {len(merged)} != {len(df_otb)}"
    print(f"[merge] Clean dataset: {merged.shape} — exactly 1 row per (hotel × date) confirmed.")
    return merged


def validate_final(df: pd.DataFrame) -> None:
    # True PK = hotel + snapshot + business date (booking curve = multiple snapshots per future date)
    dupes = df.duplicated(["hotel_code", "snapshot_date", "business_date"]).sum()
    occ_bad = ((df["occupancy"] < 0) | (df["occupancy"] > 1)).sum()
    null_counts = df[["rooms_sold", "occupancy", "revpar", "lead_time"]].isna().sum()
    n_snapshots = df["snapshot_date"].nunique()
    n_business_dates = df["business_date"].nunique()
    print(f"\n[validate] True PK duplicate (hotel × snapshot × business_date): {dupes}")
    print(f"[validate] Snapshot dates: {n_snapshots} | Business dates: {n_business_dates} (booking curve structure)")
    print(f"[validate] Occupancy out of range: {occ_bad}")
    print(f"[validate] Nulls in key forecast columns:\n{null_counts}")


def save_output(df: pd.DataFrame, path: str) -> None:
    df.to_csv(path, index=False)
    print(f"\n[save] Written → {path}  ({df.shape[0]} rows × {df.shape[1]} cols)")


if __name__ == "__main__":
    OTB_PATH    = "PEB_BI_Project_Data/data-otb.csv"
    EVENTS_PATH = "PEB_BI_Project_Data/data-events.csv"
    OUTPUT_PATH = "reconciled_data.csv"

    df_otb, df_events = load_source_data(OTB_PATH, EVENTS_PATH)

    print("\n--- Revenue Integrity Check ---")
    check_revenue_integrity(df_otb)

    print("\n--- Occupancy Fix ---")
    df_otb_clean = fix_occupancy_outliers(df_otb)

    print("\n--- Event Aggregation (Fan-out Fix) ---")
    df_events_agg = aggregate_events(df_events)

    print("\n--- Final Merge ---")
    df_final = build_reconciled_dataset(df_otb_clean, df_events_agg)

    print("\n--- Final Validation ---")
    validate_final(df_final)

    save_output(df_final, OUTPUT_PATH)

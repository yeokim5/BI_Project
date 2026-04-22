"""
1_data_prep.py
--------------
Stage 1 of the Pebblebrook BI Forecast Pipeline.

Responsibilities:
  - Load OTB and Events CSV files
  - Parse and validate date columns
  - Derive lead_time feature
  - Filter out cancelled events
  - Left-join OTB to Events on (location == market) AND (business_date == event_date)
  - Save merged result to merged_data.csv

Intended to be imported as a module or run directly.
"""

import logging
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_DIR = Path("/Users/yeomyung/Desktop/BI_Project/PEB_BI_Project_Data")
OTB_PATH = DATA_DIR / "data-otb.csv"
EVENTS_PATH = DATA_DIR / "data-events.csv"
OUTPUT_PATH = Path("/Users/yeomyung/Desktop/BI_Project/merged_data.csv")

# Columns that must be present in each source file
OTB_REQUIRED_COLS = {
    "hotel_code", "snapshot_date", "business_date",
    "rooms_sold", "adr_sold", "revenue_sold", "ooo",
    "left_to_sell", "occupancy", "revpar", "location",
}
EVENTS_REQUIRED_COLS = {
    "event_id", "market", "event_date", "name", "category",
    "location", "visitors", "influence_radius", "lat", "lon",
    "labels", "is_cancelled",
}

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module functions
# ---------------------------------------------------------------------------

def load_otb(path: Path = OTB_PATH) -> pd.DataFrame:
    """
    Load the OTB CSV file and parse date columns.

    Parameters
    ----------
    path : Path
        Absolute path to data-otb.csv.

    Returns
    -------
    pd.DataFrame
        OTB dataframe with snapshot_date and business_date as datetime64.
    """
    logger.info("Loading OTB data from: %s", path)
    if not path.exists():
        raise FileNotFoundError(f"OTB file not found: {path}")

    df = pd.read_csv(path)
    logger.info("  Raw shape: %d rows x %d cols", *df.shape)

    # Validate required columns
    missing = OTB_REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"OTB file is missing expected columns: {missing}")

    # Parse date columns
    for col in ("snapshot_date", "business_date"):
        df[col] = pd.to_datetime(df[col], format="%Y-%m-%d", errors="coerce")
        n_bad = df[col].isna().sum()
        if n_bad > 0:
            logger.warning("  %d unparseable values in OTB column '%s' — set to NaT", n_bad, col)

    logger.info("  Date range snapshot_date: %s to %s",
                df["snapshot_date"].min().date(), df["snapshot_date"].max().date())
    logger.info("  Date range business_date: %s to %s",
                df["business_date"].min().date(), df["business_date"].max().date())
    logger.info("  Hotels: %s", sorted(df["hotel_code"].dropna().unique().tolist()))
    logger.info("  Locations: %s", sorted(df["location"].dropna().unique().tolist()))
    logger.info("OTB data loaded successfully.")
    return df


def load_events(path: Path = EVENTS_PATH) -> pd.DataFrame:
    """
    Load the Events CSV file, parse event_date, and filter out cancelled events.

    Parameters
    ----------
    path : Path
        Absolute path to data-events.csv.

    Returns
    -------
    pd.DataFrame
        Events dataframe with event_date as datetime64 and no cancelled rows.
    """
    logger.info("Loading Events data from: %s", path)
    if not path.exists():
        raise FileNotFoundError(f"Events file not found: {path}")

    df = pd.read_csv(path)
    logger.info("  Raw shape: %d rows x %d cols", *df.shape)

    # Validate required columns
    missing = EVENTS_REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"Events file is missing expected columns: {missing}")

    # Parse event_date
    df["event_date"] = pd.to_datetime(df["event_date"], format="%Y-%m-%d", errors="coerce")
    n_bad = df["event_date"].isna().sum()
    if n_bad > 0:
        logger.warning("  %d unparseable values in Events column 'event_date' — set to NaT", n_bad)

    # Normalise is_cancelled to bool — handles True/False strings, 0/1, etc.
    df["is_cancelled"] = df["is_cancelled"].map(
        lambda v: str(v).strip().lower() in ("true", "1", "yes")
    )
    n_cancelled = df["is_cancelled"].sum()
    logger.info("  Cancelled events found: %d", n_cancelled)
    df = df[~df["is_cancelled"]].copy()
    logger.info("  Shape after removing cancelled events: %d rows x %d cols", *df.shape)

    logger.info("  Date range event_date: %s to %s",
                df["event_date"].min().date(), df["event_date"].max().date())
    logger.info("  Markets: %s", sorted(df["market"].dropna().unique().tolist()))
    logger.info("Events data loaded successfully.")
    return df


def derive_lead_time(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a lead_time column = (business_date - snapshot_date) in integer days.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain datetime columns business_date and snapshot_date.

    Returns
    -------
    pd.DataFrame
        Same dataframe with a new integer column 'lead_time'.
    """
    logger.info("Deriving lead_time = business_date - snapshot_date ...")
    df = df.copy()
    df["lead_time"] = (df["business_date"] - df["snapshot_date"]).dt.days

    neg = (df["lead_time"] < 0).sum()
    if neg > 0:
        logger.warning("  %d rows have negative lead_time (business_date before snapshot_date).", neg)

    logger.info("  lead_time range: %d to %d days", df["lead_time"].min(), df["lead_time"].max())
    return df


def merge_data(otb: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """
    Left-join OTB to Events on location == market AND business_date == event_date.

    A left join is used so that every OTB row is preserved even if there is no
    matching event on that date/market. Event columns will be NaN for non-event days.

    Parameters
    ----------
    otb : pd.DataFrame
        Preprocessed OTB dataframe.
    events : pd.DataFrame
        Preprocessed Events dataframe (cancelled rows already removed).

    Returns
    -------
    pd.DataFrame
        Merged dataframe.
    """
    logger.info("Merging OTB (%d rows) with Events (%d rows) ...", len(otb), len(events))

    # Rename the events 'location' column (venue) to avoid collision with OTB 'location' (market)
    events_renamed = events.rename(columns={"location": "event_venue"})

    merged = otb.merge(
        events_renamed,
        how="left",
        left_on=["location", "business_date"],
        right_on=["market", "event_date"],
    )

    logger.info("  Merged shape: %d rows x %d cols", *merged.shape)

    # Rows that matched at least one event
    matched_otb_rows = merged["event_id"].notna().sum()
    logger.info("  OTB rows matched to at least one event: %d / %d (%.1f%%)",
                matched_otb_rows, len(merged),
                100.0 * matched_otb_rows / len(merged) if len(merged) else 0)

    # Identify OTB rows that matched multiple events (fan-out check)
    n_otb_unique = otb.shape[0]
    n_merged = merged.shape[0]
    if n_merged > n_otb_unique:
        logger.info(
            "  Fan-out detected: merged has %d rows vs %d OTB rows — "
            "%d OTB rows matched multiple events on the same date.",
            n_merged, n_otb_unique, n_merged - n_otb_unique,
        )

    return merged


def save_output(df: pd.DataFrame, path: Path = OUTPUT_PATH) -> None:
    """
    Write the merged dataframe to CSV.

    Parameters
    ----------
    df : pd.DataFrame
        Final merged dataframe to persist.
    path : Path
        Destination file path.
    """
    logger.info("Saving merged data to: %s", path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    logger.info("  Saved %d rows x %d cols.", *df.shape)


def report_quality(df: pd.DataFrame) -> None:
    """
    Print a data quality summary: null counts, dtypes, and a sample.

    Parameters
    ----------
    df : pd.DataFrame
        Merged dataframe to report on.
    """
    logger.info("--- Data Quality Report ---")

    print("\n=== Merged Data Shape ===")
    print(f"  Rows   : {df.shape[0]:,}")
    print(f"  Columns: {df.shape[1]}")

    print("\n=== Null / Missing Values per Column ===")
    null_counts = df.isnull().sum()
    null_pct = (null_counts / len(df) * 100).round(1)
    null_report = pd.DataFrame({"null_count": null_counts, "null_pct": null_pct})
    # Show all columns; highlight those with nulls
    for col, row in null_report.iterrows():
        flag = " <-- has nulls" if row["null_count"] > 0 else ""
        print(f"  {col:<30} {int(row['null_count']):>6} ({row['null_pct']:.1f}%){flag}")

    print("\n=== Sample — First 5 Rows (key columns) ===")
    key_cols = [c for c in [
        "hotel_code", "snapshot_date", "business_date", "lead_time",
        "rooms_sold", "occupancy", "revpar",
        "event_id", "name", "category", "visitors", "market",
    ] if c in df.columns]
    print(df[key_cols].head(5).to_string(index=False))

    print("\n=== Additional Data Quality Checks ===")

    # Check for duplicate OTB keys
    dup_check_cols = ["hotel_code", "snapshot_date", "business_date"]
    # Only check OTB-level duplicates on a deduplicated subset
    otb_cols_present = [c for c in dup_check_cols if c in df.columns]
    if len(otb_cols_present) == len(dup_check_cols):
        n_dup = df.duplicated(subset=dup_check_cols, keep=False).sum()
        if n_dup > 0:
            print(f"  NOTE: {n_dup} rows share the same (hotel_code, snapshot_date, business_date) "
                  "— likely caused by multiple events on the same date (expected fan-out).")
        else:
            print("  No duplicate OTB keys detected (each hotel/snapshot/business_date is unique).")

    # Occupancy sanity check
    if "occupancy" in df.columns:
        occ_out = df[(df["occupancy"] < 0) | (df["occupancy"] > 1)]
        if not occ_out.empty:
            print(f"  WARNING: {len(occ_out)} rows have occupancy outside [0, 1].")
        else:
            print("  Occupancy values all within valid range [0.0, 1.0].")

    # Negative revpar check
    if "revpar" in df.columns:
        neg_revpar = (df["revpar"] < 0).sum()
        if neg_revpar > 0:
            print(f"  WARNING: {neg_revpar} rows have negative revpar.")
        else:
            print("  RevPAR values all non-negative.")

    # Lead time distribution
    if "lead_time" in df.columns:
        print(f"  lead_time stats  min={df['lead_time'].min()}  "
              f"max={df['lead_time'].max()}  "
              f"mean={df['lead_time'].mean():.1f}")

    print()


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------

def run_pipeline() -> pd.DataFrame:
    """
    Execute the full data preparation pipeline in sequence.

    Returns
    -------
    pd.DataFrame
        The final merged dataframe (also written to merged_data.csv).
    """
    logger.info("========== Stage 1: Data Preparation ==========")

    otb = load_otb()
    events = load_events()

    otb = derive_lead_time(otb)

    merged = merge_data(otb, events)

    save_output(merged)

    report_quality(merged)

    logger.info("========== Stage 1 Complete ==========")
    return merged


if __name__ == "__main__":
    run_pipeline()

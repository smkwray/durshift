"""Download primary dealer statistics from the NY Fed Markets API.

Source: https://www.newyorkfed.org/markets/counterparties/primary-dealers-statistics
API: https://markets.newyorkfed.org/api/pd/

Weekly dealer positions, transactions, and financing data.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path

import pandas as pd
import requests

from durshift.utils.files import ensure_parent_dir

logger = logging.getLogger(__name__)

BASE_URL = "https://markets.newyorkfed.org/api/pd/get"

# Key series for DurShift analysis.
# These are total Treasury (ex-TIPS) dealer position series.
DEALER_SERIES = {
    # Net positions (Long - Short) in Treasury securities ex-TIPS
    "PDPOSGST-TOT": "treasury_net_position",
    # Treasury Bills position
    "PDPOSGS-B": "treasury_bills_position",
    # Treasury Coupons < 2Y
    "PDPOSGSC-L2": "treasury_coupons_lt2y",
    # Treasury Coupons 2-3Y
    "PDPOSGSC-G2L3": "treasury_coupons_2_3y",
    # Treasury Coupons 3-6Y
    "PDPOSGSC-G3L6": "treasury_coupons_3_6y",
    # Treasury Coupons 6-7Y
    "PDPOSGSC-G6L7": "treasury_coupons_6_7y",
    # Treasury Coupons 7-11Y
    "PDPOSGSC-G7L11": "treasury_coupons_7_11y",
    # Treasury Coupons 11-21Y
    "PDPOSGSC-G11L21": "treasury_coupons_11_21y",
    # Treasury Coupons >21Y
    "PDPOSGSC-G21": "treasury_coupons_gt21y",
    # TIPS total position
    "PDPOSTIPS-TOT": "tips_net_position",
}


def fetch_dealer_series(
    series_id: str,
    timeout: int = 30,
) -> pd.DataFrame:
    """Download a single dealer statistics timeseries as CSV.

    Returns a DataFrame with columns: date, series_id, value_millions.
    """
    url = f"{BASE_URL}/{series_id}.csv"
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()

    frame = pd.read_csv(io.StringIO(response.text))
    frame.columns = ["date", "series_id", "value_millions"]
    frame["date"] = pd.to_datetime(frame["date"])
    frame["value_millions"] = pd.to_numeric(frame["value_millions"], errors="coerce")
    return frame


def fetch_dealer_positions(
    series_map: dict[str, str] | None = None,
    timeout: int = 30,
) -> pd.DataFrame:
    """Download multiple dealer position series and pivot into a wide DataFrame.

    Parameters
    ----------
    series_map : dict[str, str] | None
        Mapping from NY Fed series ID to friendly column name.
        Defaults to DEALER_SERIES.
    timeout : int
        HTTP timeout per request.

    Returns
    -------
    pd.DataFrame
        Weekly observations indexed by date, one column per series.
        Values are in millions of dollars.
    """
    use_map = series_map or DEALER_SERIES
    frames: list[pd.DataFrame] = []

    for series_id, col_name in use_map.items():
        try:
            df = fetch_dealer_series(series_id, timeout=timeout)
            df = df.rename(columns={"value_millions": col_name})[["date", col_name]]
            frames.append(df)
            logger.info("Fetched %s (%d obs)", series_id, len(df))
        except Exception as exc:
            logger.warning("Failed to fetch %s: %s", series_id, exc)

    if not frames:
        return pd.DataFrame()

    # Merge all series on date
    result = frames[0]
    for df in frames[1:]:
        result = result.merge(df, on="date", how="outer")

    result = result.set_index("date").sort_index()
    logger.info("Built dealer positions: %d rows, %d columns", len(result), len(result.columns))
    return result


def fetch_and_save_dealer_positions(
    destination: str | Path,
    series_map: dict[str, str] | None = None,
) -> Path:
    """Download dealer positions and save as CSV."""
    frame = fetch_dealer_positions(series_map=series_map)
    output_path = ensure_parent_dir(destination)
    frame.to_csv(output_path)
    logger.info("Saved dealer positions (%d rows) to %s", len(frame), output_path)
    return output_path

"""Download H.15 Selected Interest Rates from the Federal Reserve Board.

Source: https://www.federalreserve.gov/releases/h15/
Downloads daily Treasury constant maturity rates (1M through 30Y).
"""

from __future__ import annotations

import io
import logging
from pathlib import Path

import pandas as pd
import requests

from durshift.utils.files import ensure_parent_dir

logger = logging.getLogger(__name__)

# Federal Reserve Data Download Program URL for Treasury constant maturity rates.
# Series ID bf17364827e38702b42a58cf8eaa3f78 covers all CMT tenors.
H15_URL = (
    "https://www.federalreserve.gov/datadownload/Output.aspx"
    "?rel=H15&series=bf17364827e38702b42a58cf8eaa3f78"
    "&lastobs=&from={start}&to={end}"
    "&filetype=csv&label=include&layout=seriescolumn"
)

# Friendly column names for the raw series IDs.
TENOR_MAP = {
    "RIFLGFCM01_N.B": "cmt_1m",
    "RIFLGFCM03_N.B": "cmt_3m",
    "RIFLGFCM06_N.B": "cmt_6m",
    "RIFLGFCY01_N.B": "cmt_1y",
    "RIFLGFCY02_N.B": "cmt_2y",
    "RIFLGFCY03_N.B": "cmt_3y",
    "RIFLGFCY05_N.B": "cmt_5y",
    "RIFLGFCY07_N.B": "cmt_7y",
    "RIFLGFCY10_N.B": "cmt_10y",
    "RIFLGFCY20_N.B": "cmt_20y",
    "RIFLGFCY30_N.B": "cmt_30y",
}


def fetch_h15_rates(
    start: str = "01/01/2020",
    end: str = "",
    timeout: int = 60,
) -> pd.DataFrame:
    """Download daily H.15 Treasury constant maturity rates.

    Parameters
    ----------
    start, end : str
        Date range in MM/DD/YYYY format (Fed DDP convention).
    timeout : int
        HTTP timeout in seconds.

    Returns
    -------
    pd.DataFrame
        Daily observations with date index and tenor columns (cmt_1m .. cmt_30y).
    """
    if not end:
        end = pd.Timestamp.today().strftime("%m/%d/%Y")
    url = H15_URL.format(start=start, end=end)
    logger.info("Downloading H.15 rates from %s to %s ...", start, end)
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()

    # The CSV has 5 header rows before the data starts.
    # Row 0: Series Description (long names)
    # Row 1: Unit
    # Row 2: Multiplier
    # Row 3: Currency
    # Row 4: Unique Identifier (series IDs)
    # Row 5: Column headers (Time Period + series IDs)
    # Row 6+: data
    lines = response.text.strip().split("\n")

    # Find the data header row (starts with "Time Period")
    header_idx = None
    for i, line in enumerate(lines):
        if line.startswith('"Time Period"'):
            header_idx = i
            break

    if header_idx is None:
        raise ValueError("Could not find 'Time Period' header in H.15 CSV")

    data_text = "\n".join(lines[header_idx:])
    frame = pd.read_csv(io.StringIO(data_text))

    # Rename columns
    frame = frame.rename(columns={"Time Period": "date"})
    frame = frame.rename(columns=TENOR_MAP)
    frame["date"] = pd.to_datetime(frame["date"])

    # Convert rate columns to numeric (ND = no data)
    tenor_cols = [c for c in frame.columns if c.startswith("cmt_")]
    for col in tenor_cols:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")

    frame = frame.set_index("date").sort_index()
    logger.info("Fetched %d daily H.15 observations, %d tenors", len(frame), len(tenor_cols))
    return frame


def fetch_and_save_h15(
    destination: str | Path,
    start: str = "01/01/2020",
    end: str = "",
) -> Path:
    """Download H.15 rates and save as CSV."""
    if not end:
        end = pd.Timestamp.today().strftime("%m/%d/%Y")
    frame = fetch_h15_rates(start=start, end=end)
    output_path = ensure_parent_dir(destination)
    frame.to_csv(output_path)
    logger.info("Saved H.15 rates (%d rows) to %s", len(frame), output_path)
    return output_path


def interpolate_yield_for_maturity(
    rates: pd.DataFrame,
    date: pd.Timestamp,
    maturity_years: float,
) -> float | None:
    """Look up an approximate yield for a given date and maturity.

    Uses linear interpolation between the two nearest CMT tenors.
    Returns None if the date is not in the rates index.
    """
    if date not in rates.index:
        # Try nearest business day
        nearest = rates.index[rates.index.get_indexer([date], method="nearest")[0]]
        if abs((nearest - date).days) > 5:
            return None
        date = nearest

    row = rates.loc[date]
    tenors = [
        (1 / 12, "cmt_1m"),
        (3 / 12, "cmt_3m"),
        (6 / 12, "cmt_6m"),
        (1, "cmt_1y"),
        (2, "cmt_2y"),
        (3, "cmt_3y"),
        (5, "cmt_5y"),
        (7, "cmt_7y"),
        (10, "cmt_10y"),
        (20, "cmt_20y"),
        (30, "cmt_30y"),
    ]

    # Find bracketing tenors
    below = None
    above = None
    for years, col in tenors:
        val = row.get(col)
        if pd.isna(val):
            continue
        if years <= maturity_years:
            below = (years, float(val))
        if years >= maturity_years and above is None:
            above = (years, float(val))

    if below is None and above is None:
        return None
    if below is None:
        return above[1] / 100.0
    if above is None:
        return below[1] / 100.0
    if below[0] == above[0]:
        return below[1] / 100.0

    # Linear interpolation
    weight = (maturity_years - below[0]) / (above[0] - below[0])
    rate = below[1] + weight * (above[1] - below[1])
    return rate / 100.0


# --- TIPS real yield support ---

TIPS_TENOR_MAP = {
    "RIFLGFCY05_XII_N.B": "tips_5y",
    "RIFLGFCY07_XII_N.B": "tips_7y",
    "RIFLGFCY10_XII_N.B": "tips_10y",
    "RIFLGFCY20_XII_N.B": "tips_20y",
    "RIFLGFCY30_XII_N.B": "tips_30y",
}


H15_BULK_ZIP_URL = "https://www.federalreserve.gov/datadownload/Output.aspx?rel=H15&filetype=zip"


def fetch_and_save_tips_real_yields(
    destination: str | Path,
    timeout: int = 120,
) -> Path:
    """Download the H.15 bulk XML zip, extract TIPS real yield series, and save as CSV.

    The bulk XML contains all H.15 series.  We extract the daily TIPS real yield
    series whose IDs match ``RIFLGFCY*_XII_N.B`` and pivot to a DataFrame with a
    date index and columns tips_5y, tips_7y, tips_10y, tips_20y, tips_30y.

    Parameters
    ----------
    destination : str | Path
        File path for the output CSV.
    timeout : int
        HTTP timeout in seconds for the bulk download.

    Returns
    -------
    Path
        The written CSV path.
    """
    import tempfile
    import zipfile
    from xml.etree import ElementTree

    logger.info("Downloading H.15 bulk XML zip ...")
    response = requests.get(H15_BULK_ZIP_URL, timeout=timeout)
    response.raise_for_status()

    # Write zip to a temp file and extract
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "h15.zip"
        zip_path.write_bytes(response.content)

        with zipfile.ZipFile(zip_path) as zf:
            xml_names = [n for n in zf.namelist() if n.endswith(".xml")]
            if not xml_names:
                raise ValueError("No XML file found in H.15 bulk zip")
            xml_bytes = zf.read(xml_names[0])

    # Parse the XML
    root = ElementTree.fromstring(xml_bytes)

    # We need to find Series elements whose SERIES_NAME matches TIPS tenor IDs
    tips_series_ids = set(TIPS_TENOR_MAP.keys())

    records: dict[str, dict[str, float]] = {}  # date -> {series_id: value}

    # Walk the tree looking for Series / Obs elements
    for series_el in root.iter():
        tag = series_el.tag.split("}")[-1] if "}" in series_el.tag else series_el.tag
        if tag != "Series":
            continue

        series_name = series_el.attrib.get("SERIES_NAME", "")
        if series_name not in tips_series_ids:
            continue

        friendly = TIPS_TENOR_MAP[series_name]
        for obs_el in series_el:
            obs_tag = obs_el.tag.split("}")[-1] if "}" in obs_el.tag else obs_el.tag
            if obs_tag != "Obs":
                continue
            date_str = obs_el.attrib.get("TIME_PERIOD", "")
            val_str = obs_el.attrib.get("OBS_VALUE", "")
            if not date_str or not val_str:
                continue
            try:
                val = float(val_str)
            except ValueError:
                continue
            records.setdefault(date_str, {})[friendly] = val

    if not records:
        raise ValueError("No TIPS real yield observations found in H.15 bulk XML")

    frame = pd.DataFrame.from_dict(records, orient="index")
    frame.index = pd.to_datetime(frame.index)
    frame.index.name = "date"
    frame = frame.sort_index()

    # Ensure all expected columns exist
    for col in ["tips_5y", "tips_7y", "tips_10y", "tips_20y", "tips_30y"]:
        if col not in frame.columns:
            frame[col] = float("nan")
    frame = frame[["tips_5y", "tips_7y", "tips_10y", "tips_20y", "tips_30y"]]

    output_path = ensure_parent_dir(destination)
    frame.to_csv(output_path)
    logger.info("Saved TIPS real yields (%d rows) to %s", len(frame), output_path)
    return output_path


def load_tips_real_yields(path: str | Path) -> pd.DataFrame:
    """Load TIPS real yield CSV (extracted from H.15 bulk XML).

    Parameters
    ----------
    path : str | Path
        Path to the tips_real_yields.csv file.

    Returns
    -------
    pd.DataFrame
        Daily TIPS real yields indexed by date with columns tips_5y..tips_30y.
    """
    frame = pd.read_csv(path, index_col=0, parse_dates=True)
    frame = frame.rename(columns=TIPS_TENOR_MAP)
    for col in frame.columns:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame


def interpolate_tips_yield(
    tips_rates: pd.DataFrame,
    date: pd.Timestamp,
    maturity_years: float,
) -> float | None:
    """Look up a TIPS real yield for a given date and maturity.

    Uses linear interpolation between the nearest TIPS CMT tenors.
    """
    if date not in tips_rates.index:
        nearest = tips_rates.index[tips_rates.index.get_indexer([date], method="nearest")[0]]
        if abs((nearest - date).days) > 5:
            return None
        date = nearest

    row = tips_rates.loc[date]
    tenors = [
        (5, "tips_5y"),
        (7, "tips_7y"),
        (10, "tips_10y"),
        (20, "tips_20y"),
        (30, "tips_30y"),
    ]

    below = None
    above = None
    for years, col in tenors:
        val = row.get(col)
        if pd.isna(val):
            continue
        if years <= maturity_years:
            below = (years, float(val))
        if years >= maturity_years and above is None:
            above = (years, float(val))

    if below is None and above is None:
        return None
    if below is None:
        return above[1] / 100.0
    if above is None:
        return below[1] / 100.0
    if below[0] == above[0]:
        return below[1] / 100.0

    weight = (maturity_years - below[0]) / (above[0] - below[0])
    rate = below[1] + weight * (above[1] - below[1])
    return rate / 100.0

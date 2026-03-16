"""Download SOMA (System Open Market Account) holdings from the NY Fed.

Source: https://www.newyorkfed.org/markets/soma-holdings
API: https://markets.newyorkfed.org/api/soma/

Weekly summary of Fed Treasury holdings by type (Bills, Notes & Bonds,
TIPS, FRN, Agencies, MBS).
"""

from __future__ import annotations

import io
import logging
from pathlib import Path

import pandas as pd
import requests

from durshift.utils.files import ensure_parent_dir

logger = logging.getLogger(__name__)

SOMA_SUMMARY_URL = "https://markets.newyorkfed.org/api/soma/summary.csv"

SUMMARY_RENAME = {
    "As Of Date": "date",
    "Total": "total",
    "Bills": "bills",
    "Notes & Bonds": "notes_bonds",
    "TIPS": "tips",
    "FRN": "frn",
    "TIPS Inflation Compensation": "tips_inflation_comp",
    "Agencies": "agencies",
    "MBS": "mbs",
    "CMBS": "cmbs",
}


def fetch_soma_summary(timeout: int = 30) -> pd.DataFrame:
    """Download the weekly SOMA holdings summary.

    Returns a DataFrame indexed by date with columns for each asset class
    (total, bills, notes_bonds, tips, frn, mbs, etc.) in dollars.
    """
    logger.info("Downloading SOMA summary...")
    response = requests.get(SOMA_SUMMARY_URL, timeout=timeout)
    response.raise_for_status()

    frame = pd.read_csv(io.StringIO(response.text))
    frame = frame.rename(columns=SUMMARY_RENAME)

    if "date" not in frame.columns:
        raise ValueError("SOMA summary CSV missing 'As Of Date' column")

    frame["date"] = pd.to_datetime(frame["date"])

    # Convert numeric columns
    for col in frame.columns:
        if col != "date":
            frame[col] = pd.to_numeric(frame[col], errors="coerce")

    frame = frame.set_index("date").sort_index()
    logger.info("Fetched SOMA summary: %d observations", len(frame))
    return frame


def fetch_and_save_soma_summary(
    destination: str | Path,
    timeout: int = 30,
) -> Path:
    """Download SOMA summary and save as CSV."""
    frame = fetch_soma_summary(timeout=timeout)
    output_path = ensure_parent_dir(destination)
    frame.to_csv(output_path)
    logger.info("Saved SOMA summary (%d rows) to %s", len(frame), output_path)
    return output_path

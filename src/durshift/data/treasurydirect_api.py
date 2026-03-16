"""Client for the TreasuryDirect TA_WS securities search API.

The Fiscal Data API does include TIPS and FRN auctions, but it returns them
with a generic security_type (e.g. "Note") that does not distinguish TIPS
from nominal notes or FRN from fixed-rate notes. This client queries the
TreasuryDirect TA_WS endpoint and adds an explicit ``asset_class`` column
(``"TIPS"`` or ``"FRN"``) so downstream analytics can filter by inflation-
linked vs floating-rate securities without ambiguity.

Source: https://treasurydirect.gov/TA_WS/securities/search
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import requests

from durshift.utils.files import ensure_parent_dir

logger = logging.getLogger(__name__)

BASE_URL = "https://treasurydirect.gov/TA_WS/securities/search"

# Fields we keep from the full response.
KEEP_FIELDS = [
    "cusip",
    "securityType",
    "securityTerm",
    "auctionDate",
    "issueDate",
    "maturityDate",
    "interestRate",
    "highYield",
    "pricePer100",
    "offeringAmount",
    "competitiveAccepted",
    "competitiveTendered",
    "directBidderAccepted",
    "indirectBidderAccepted",
    "bidToCoverRatio",
    "reopening",
    "somaAccepted",
    "announcementDate",
]

# Friendly column names matching the Fiscal Data schema where possible.
RENAME_MAP = {
    "securityType": "security_type",
    "securityTerm": "security_term",
    "auctionDate": "auction_date",
    "issueDate": "issue_date",
    "maturityDate": "maturity_date",
    "interestRate": "int_rate",
    "highYield": "high_yield",
    "pricePer100": "price_per100",
    "offeringAmount": "offering_amt",
    "competitiveAccepted": "comp_accepted",
    "competitiveTendered": "comp_tendered",
    "directBidderAccepted": "direct_bidder_accepted",
    "indirectBidderAccepted": "indirect_bidder_accepted",
    "bidToCoverRatio": "bid_to_cover_ratio",
    "somaAccepted": "soma_accepted",
    "announcementDate": "announcement_date",
}


def fetch_securities(
    security_type: str,
    start_date: str = "2020-01-01",
    page_size: int = 250,
    timeout: int = 30,
) -> pd.DataFrame:
    """Download securities of a given type from the TreasuryDirect API.

    Parameters
    ----------
    security_type : str
        E.g. "TIPS", "FRN", "Bond", "Note", "Bill".
    start_date : str
        Earliest auction date (YYYY-MM-DD).
    page_size : int
        Records per request (max ~250 for this API).
    timeout : int
        HTTP timeout.

    Returns
    -------
    pd.DataFrame
        Auction records with standardised column names.
    """
    params = {
        "format": "json",
        "type": security_type,
        "pagesize": str(page_size),
        "startDate": start_date,
    }
    logger.info("Fetching %s auctions from TreasuryDirect (since %s)...", security_type, start_date)
    response = requests.get(BASE_URL, params=params, timeout=timeout)
    response.raise_for_status()
    records = response.json()

    if not records:
        logger.info("No %s records returned.", security_type)
        return pd.DataFrame()

    frame = pd.DataFrame(records)

    # Keep only the fields we care about (some may be absent)
    keep = [c for c in KEEP_FIELDS if c in frame.columns]
    frame = frame[keep].copy()
    frame = frame.rename(columns=RENAME_MAP)

    # Clean date columns
    for col in ["auction_date", "issue_date", "maturity_date", "announcement_date"]:
        if col in frame.columns:
            frame[col] = pd.to_datetime(frame[col], errors="coerce").dt.strftime("%Y-%m-%d")

    # Clean numeric columns
    for col in ["int_rate", "high_yield", "price_per100", "offering_amt", "bid_to_cover_ratio"]:
        if col in frame.columns:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")

    frame["asset_class"] = security_type
    frame = frame.sort_values("auction_date", ascending=False).reset_index(drop=True)
    logger.info("Fetched %d %s auction records.", len(frame), security_type)
    return frame


def fetch_tips_and_frn(
    start_date: str = "2020-01-01",
    timeout: int = 30,
) -> pd.DataFrame:
    """Fetch both TIPS and FRN auctions and combine."""
    tips = fetch_securities("TIPS", start_date=start_date, timeout=timeout)
    frn = fetch_securities("FRN", start_date=start_date, timeout=timeout)
    combined = pd.concat([tips, frn], ignore_index=True)
    combined = combined.sort_values("auction_date", ascending=False).reset_index(drop=True)
    logger.info("Combined TIPS+FRN: %d records.", len(combined))
    return combined


def fetch_and_save_tips_frn(
    destination: str | Path,
    start_date: str = "2020-01-01",
) -> Path:
    """Fetch TIPS+FRN auctions and save as CSV."""
    frame = fetch_tips_and_frn(start_date=start_date)
    output_path = ensure_parent_dir(destination)
    frame.to_csv(output_path, index=False)
    logger.info("Saved %d TIPS+FRN records to %s", len(frame), output_path)
    return output_path

"""Client for the U.S. Treasury Fiscal Data API.

Provides paginated download of Treasury Securities Auctions data from
https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query

All responses are returned as pandas DataFrames. Raw JSON snapshots can
optionally be saved for reproducibility.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd
import requests

from durshift.utils.files import ensure_parent_dir

logger = logging.getLogger(__name__)

BASE_URL = (
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
    "/v1/accounting/od/auctions_query"
)

# Fields relevant to DurShift's operation-panel and issuance-context work.
DEFAULT_FIELDS = [
    "cusip",
    "security_type",
    "security_term",
    "auction_date",
    "issue_date",
    "maturity_date",
    "int_rate",
    "high_yield",
    "price_per100",
    "offering_amt",
    "comp_accepted",
    "comp_tendered",
    "direct_bidder_accepted",
    "indirect_bidder_accepted",
    "primary_dealer_accepted",
    "bid_to_cover_ratio",
    "reopening",
    "soma_accepted",
]

# Maximum page size the API supports.
MAX_PAGE_SIZE = 10_000


def fetch_auctions(
    *,
    fields: list[str] | None = None,
    filters: dict[str, str] | None = None,
    min_auction_date: str | None = None,
    security_types: list[str] | None = None,
    sort: str = "-auction_date",
    page_size: int = MAX_PAGE_SIZE,
    timeout: int = 60,
) -> pd.DataFrame:
    """Download Treasury auction records from the Fiscal Data API.

    Parameters
    ----------
    fields : list[str] | None
        Columns to retrieve. Defaults to DEFAULT_FIELDS.
    filters : dict[str, str] | None
        Raw API filter expressions, e.g. ``{"auction_date": "gte:2020-01-01"}``.
    min_auction_date : str | None
        Convenience shorthand for ``filters={"auction_date": "gte:<date>"}``.
    security_types : list[str] | None
        Filter to specific types, e.g. ``["Bill", "Note", "Bond", "TIPS", "FRN"]``.
    sort : str
        API sort expression. Default is newest first.
    page_size : int
        Records per page (max 10 000).
    timeout : int
        HTTP request timeout in seconds.

    Returns
    -------
    pd.DataFrame
        All matching auction records across pages.
    """
    use_fields = fields or DEFAULT_FIELDS

    filter_parts: list[str] = []
    if filters:
        for key, expr in filters.items():
            filter_parts.append(f"{key}:{expr}")
    if min_auction_date:
        filter_parts.append(f"auction_date:gte:{min_auction_date}")
    if security_types:
        inner = ",".join(security_types)
        filter_parts.append(f"security_type:in:({inner})")

    params: dict[str, str] = {
        "fields": ",".join(use_fields),
        "sort": sort,
        "page[size]": str(min(page_size, MAX_PAGE_SIZE)),
        "format": "json",
    }
    if filter_parts:
        params["filter"] = ",".join(filter_parts)

    all_records: list[dict] = []
    page_number = 1

    while True:
        params["page[number]"] = str(page_number)
        logger.info("Fiscal Data API page %d ...", page_number)
        response = requests.get(BASE_URL, params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        records = payload.get("data", [])
        all_records.extend(records)

        meta = payload.get("meta", {})
        total_pages = meta.get("total-pages", 1)
        if page_number >= total_pages:
            break
        page_number += 1

    logger.info("Fetched %d auction records.", len(all_records))
    if not all_records:
        return pd.DataFrame(columns=use_fields)
    return pd.DataFrame(all_records)


def fetch_and_save_auctions(
    destination: str | Path,
    **kwargs,
) -> Path:
    """Fetch auction data and save as CSV. Returns the output path.

    Accepts the same keyword arguments as :func:`fetch_auctions`.
    """
    frame = fetch_auctions(**kwargs)
    output_path = ensure_parent_dir(destination)
    frame.to_csv(output_path, index=False)
    logger.info("Saved %d records to %s", len(frame), output_path)
    return output_path


def save_raw_json_snapshot(
    destination: str | Path,
    **kwargs,
) -> Path:
    """Fetch auction data and save the raw JSON for reproducibility.

    Useful for keeping an immutable snapshot of exactly what the API returned.
    """
    use_fields = kwargs.pop("fields", None) or DEFAULT_FIELDS

    filter_parts: list[str] = []
    filters = kwargs.pop("filters", None)
    if filters:
        for key, expr in filters.items():
            filter_parts.append(f"{key}:{expr}")
    min_date = kwargs.pop("min_auction_date", None)
    if min_date:
        filter_parts.append(f"auction_date:gte:{min_date}")
    sec_types = kwargs.pop("security_types", None)
    if sec_types:
        inner = ",".join(sec_types)
        filter_parts.append(f"security_type:in:({inner})")

    sort = kwargs.pop("sort", "-auction_date")
    page_size = kwargs.pop("page_size", MAX_PAGE_SIZE)
    timeout = kwargs.pop("timeout", 60)

    params: dict[str, str] = {
        "fields": ",".join(use_fields),
        "sort": sort,
        "page[size]": str(min(page_size, MAX_PAGE_SIZE)),
        "format": "json",
    }
    if filter_parts:
        params["filter"] = ",".join(filter_parts)

    all_records: list[dict] = []
    page_number = 1

    while True:
        params["page[number]"] = str(page_number)
        response = requests.get(BASE_URL, params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        records = payload.get("data", [])
        all_records.extend(records)
        meta = payload.get("meta", {})
        total_pages = meta.get("total-pages", 1)
        if page_number >= total_pages:
            break
        page_number += 1

    output_path = ensure_parent_dir(destination)
    output_path.write_text(json.dumps(all_records, indent=2), encoding="utf-8")
    logger.info("Saved raw JSON snapshot (%d records) to %s", len(all_records), output_path)
    return output_path

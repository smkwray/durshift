"""Parse the Treasury buyback schedule XML.

The current (tentative) buyback calendar is published as XML at:
  https://home.treasury.gov/system/files/221/Tentative-Buyback-Schedule.xml

This module downloads and parses that schedule into a structured DataFrame.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import requests

from durshift.utils.files import ensure_parent_dir

logger = logging.getLogger(__name__)

SCHEDULE_URL = "https://home.treasury.gov/system/files/221/Tentative-Buyback-Schedule.xml"

# Fields extracted from each <BuybackCalendarDate> element.
SCHEDULE_COLUMNS = [
    "purchase_bucket",
    "security_type",
    "operation_type",
    "min_purchase_amount",
    "max_purchase_amount",
    "maturity_range_start",
    "maturity_range_end",
    "announcement_date",
    "operation_date",
    "settlement_date",
    "operation_start_time_et",
    "operation_end_time_et",
]

# Maps XML tag names to our column names.
_TAG_MAP = {
    "PurchaseBucketName": "purchase_bucket",
    "SecurityType": "security_type",
    "OperationType": "operation_type",
    "MinimumPurchaseAmountDollars": "min_purchase_amount",
    "MaximumPurchaseAmountDollars": "max_purchase_amount",
    "MaturityDateRangeStart": "maturity_range_start",
    "MaturityDateRangeEnd": "maturity_range_end",
    "AnnouncementDate": "announcement_date",
    "OperationDate": "operation_date",
    "SettlementDate": "settlement_date",
    "OperationStartTimeEasternUS": "operation_start_time_et",
    "OperationEndTimeEasternUS": "operation_end_time_et",
}


def download_schedule_xml(destination: str | Path, timeout: int = 30) -> Path:
    """Download the current buyback schedule XML and save it."""
    output_path = ensure_parent_dir(destination)
    response = requests.get(SCHEDULE_URL, timeout=timeout)
    response.raise_for_status()
    output_path.write_bytes(response.content)
    logger.info("Saved buyback schedule XML to %s", output_path)
    return output_path


def parse_schedule_xml(xml_path: str | Path) -> tuple[dict, pd.DataFrame]:
    """Parse a saved buyback schedule XML file.

    Returns
    -------
    metadata : dict
        Calendar-level metadata (name, start_date, end_date).
    schedule : pd.DataFrame
        One row per scheduled buyback operation with SCHEDULE_COLUMNS.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    metadata = {
        "calendar_name": _text(root, "BuybackCalendarName"),
        "start_date": _text(root, "StartDate"),
        "end_date": _text(root, "EndDate"),
    }

    rows: list[dict] = []
    for entry in root.findall("BuybackCalendarDate"):
        row: dict = {}
        for xml_tag, col_name in _TAG_MAP.items():
            row[col_name] = _text(entry, xml_tag)
        rows.append(row)

    frame = pd.DataFrame(rows, columns=SCHEDULE_COLUMNS)

    # Convert numeric and date columns.
    for col in ["min_purchase_amount", "max_purchase_amount"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    for col in [
        "maturity_range_start",
        "maturity_range_end",
        "announcement_date",
        "operation_date",
        "settlement_date",
    ]:
        frame[col] = pd.to_datetime(frame[col], errors="coerce")

    logger.info(
        "Parsed %d operations from schedule '%s'",
        len(frame),
        metadata.get("calendar_name", "unknown"),
    )
    return metadata, frame


def fetch_and_save_schedule(
    xml_destination: str | Path,
    csv_destination: str | Path,
    timeout: int = 30,
) -> tuple[Path, Path]:
    """Download the schedule XML, parse it, and save as CSV.

    Returns the paths to the saved XML and CSV files.
    """
    xml_path = download_schedule_xml(xml_destination, timeout=timeout)
    _metadata, frame = parse_schedule_xml(xml_path)
    csv_path = ensure_parent_dir(csv_destination)
    frame.to_csv(csv_path, index=False)
    logger.info("Saved parsed schedule (%d rows) to %s", len(frame), csv_path)
    return xml_path, csv_path


def _text(element: ET.Element, tag: str) -> str | None:
    """Extract text from a child element, or None if missing."""
    child = element.find(tag)
    return child.text if child is not None else None

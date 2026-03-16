from __future__ import annotations

from pathlib import Path

import pandas as pd

from durshift.analytics.classification import classify_operation
from durshift.analytics.duration import dv01, maturity_bucket, modified_duration
from durshift.data.contracts import (
    BUYBACK_INPUT_COLUMNS,
    OPERATION_PANEL_COLUMNS,
    validate_required_columns,
)
from durshift.utils.files import ensure_parent_dir


def normalize_operation_panel(frame: pd.DataFrame) -> pd.DataFrame:
    """Build the canonical first-pass operation panel from a raw input frame."""

    validate_required_columns(frame, BUYBACK_INPUT_COLUMNS, "buyback input frame")
    working = frame.copy()

    date_columns = ["announcement_date", "operation_date", "issue_date"]
    for column in date_columns:
        working[column] = pd.to_datetime(working[column], utc=False)

    numeric_columns = [
        "maturity_years",
        "coupon_rate",
        "accepted_amount",
        "offered_amount",
    ]
    for column in numeric_columns:
        working[column] = pd.to_numeric(working[column], errors="coerce")

    if "yield_proxy" not in working.columns:
        working["yield_proxy"] = working["coupon_rate"].fillna(0.04)
    else:
        working["yield_proxy"] = pd.to_numeric(working["yield_proxy"], errors="coerce").fillna(
            working["coupon_rate"].fillna(0.04)
        )

    if "replacement_maturity_years" not in working.columns:
        working["replacement_maturity_years"] = pd.NA

    if "notes" not in working.columns:
        working["notes"] = ""

    working["accepted_share"] = working["accepted_amount"] / working["offered_amount"]
    working["issue_age_days"] = (working["operation_date"] - working["issue_date"]).dt.days.astype(
        "Int64"
    )
    working["purpose_label"] = working.apply(
        lambda row: classify_operation(
            security_type=str(row["security_type"]),
            maturity_years=float(row["maturity_years"]),
            stated_purpose=str(row.get("stated_purpose", "")),
            notes=str(row.get("notes", "")),
        ),
        axis=1,
    )
    working["maturity_bucket"] = working["maturity_years"].map(maturity_bucket)
    working["replacement_maturity_bucket"] = working["replacement_maturity_years"].map(
        lambda value: maturity_bucket(float(value)) if pd.notna(value) else pd.NA
    )
    working["modified_duration"] = working.apply(
        lambda row: modified_duration(
            coupon_rate=float(row["coupon_rate"]),
            yield_rate=float(row["yield_proxy"]),
            maturity_years=float(row["maturity_years"]),
        ),
        axis=1,
    )
    working["dv01"] = working.apply(
        lambda row: dv01(
            par_amount=float(row["accepted_amount"]),
            coupon_rate=float(row["coupon_rate"]),
            yield_rate=float(row["yield_proxy"]),
            maturity_years=float(row["maturity_years"]),
        ),
        axis=1,
    )
    working["duration_dollars"] = working["accepted_amount"] * working["modified_duration"]

    validate_required_columns(working, OPERATION_PANEL_COLUMNS, "operation panel")

    return working[OPERATION_PANEL_COLUMNS].sort_values("operation_date").reset_index(drop=True)


def build_operation_panel(input_path: str | Path, output_path: str | Path) -> Path:
    """Load a CSV input file and write the normalized operation panel."""

    input_file = Path(input_path)
    frame = pd.read_csv(input_file)
    panel = normalize_operation_panel(frame)
    output_file = ensure_parent_dir(output_path)
    panel.to_csv(output_file, index=False)
    return output_file

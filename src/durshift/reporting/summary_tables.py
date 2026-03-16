from __future__ import annotations

from pathlib import Path

import pandas as pd

from durshift.data.contracts import validate_required_columns
from durshift.utils.files import ensure_parent_dir

SUMMARY_REQUIRED_COLUMNS = [
    "purpose_label",
    "maturity_bucket",
    "accepted_amount",
    "modified_duration",
    "duration_dollars",
    "operation_date",
]


def build_duration_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Aggregate operation-level data into a simple duration summary table."""

    # Support both sample panel column name and real panel column name.
    working = frame.copy()
    if "par_amount_accepted" in working.columns and "accepted_amount" not in working.columns:
        working["accepted_amount"] = working["par_amount_accepted"]

    validate_required_columns(working, SUMMARY_REQUIRED_COLUMNS, "operation panel for summary")
    summary = (
        working.groupby(["purpose_label", "maturity_bucket"], dropna=False)
        .agg(
            operations=("operation_date", "nunique"),
            total_accepted_amount=("accepted_amount", "sum"),
            avg_modified_duration=("modified_duration", "mean"),
            total_duration_dollars=("duration_dollars", "sum"),
        )
        .reset_index()
        .sort_values(["purpose_label", "maturity_bucket"])
    )
    return summary


def write_duration_summary(input_path: str | Path, output_path: str | Path) -> Path:
    """Read a panel CSV, write a summary CSV, and return the output path."""

    frame = pd.read_csv(input_path)
    summary = build_duration_summary(frame)
    output_file = ensure_parent_dir(output_path)
    summary.to_csv(output_file, index=False)
    return output_file

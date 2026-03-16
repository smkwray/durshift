from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

BUYBACK_INPUT_COLUMNS = [
    "announcement_date",
    "operation_date",
    "security_type",
    "maturity_years",
    "coupon_rate",
    "accepted_amount",
    "offered_amount",
    "issue_date",
    "stated_purpose",
    "buyback_bucket",
]

OPERATION_PANEL_COLUMNS = [
    "announcement_date",
    "operation_date",
    "security_type",
    "maturity_years",
    "coupon_rate",
    "yield_proxy",
    "accepted_amount",
    "offered_amount",
    "accepted_share",
    "issue_date",
    "issue_age_days",
    "stated_purpose",
    "purpose_label",
    "buyback_bucket",
    "maturity_bucket",
    "replacement_maturity_years",
    "replacement_maturity_bucket",
    "modified_duration",
    "dv01",
    "duration_dollars",
    "notes",
]


def validate_required_columns(
    frame: pd.DataFrame,
    required_columns: Sequence[str],
    dataset_name: str,
) -> None:
    """Raise a helpful error when a frame does not satisfy its required schema."""

    missing = [column for column in required_columns if column not in frame.columns]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"{dataset_name} is missing required columns: {joined}")

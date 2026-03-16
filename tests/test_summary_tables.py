from __future__ import annotations

import pandas as pd

from durshift.reporting.summary_tables import build_duration_summary


def test_build_duration_summary_aggregates_by_purpose_and_bucket():
    frame = pd.DataFrame(
        {
            "purpose_label": ["liquidity_support", "liquidity_support", "cash_management"],
            "maturity_bucket": ["5-10Y", "5-10Y", "0-2Y"],
            "accepted_amount": [1_000_000, 2_000_000, 500_000],
            "modified_duration": [6.0, 7.0, 1.5],
            "duration_dollars": [6_000_000, 14_000_000, 750_000],
            "operation_date": ["2025-02-01", "2025-03-01", "2025-04-01"],
        }
    )
    result = build_duration_summary(frame)
    assert len(result) == 2
    liq_row = result[result["purpose_label"] == "liquidity_support"].iloc[0]
    assert liq_row["operations"] == 2
    assert liq_row["total_accepted_amount"] == 3_000_000
    assert liq_row["total_duration_dollars"] == 20_000_000


def test_build_duration_summary_counts_unique_operation_dates():
    """Multiple securities on the same operation date should count as 1 operation."""
    frame = pd.DataFrame(
        {
            "purpose_label": ["liquidity_support"] * 3,
            "maturity_bucket": ["5-10Y"] * 3,
            "accepted_amount": [1_000_000, 2_000_000, 500_000],
            "modified_duration": [6.0, 7.0, 5.0],
            "duration_dollars": [6_000_000, 14_000_000, 2_500_000],
            "operation_date": ["2025-02-01", "2025-02-01", "2025-03-01"],
        }
    )
    result = build_duration_summary(frame)
    assert len(result) == 1
    # 3 rows but only 2 unique dates
    assert result.iloc[0]["operations"] == 2

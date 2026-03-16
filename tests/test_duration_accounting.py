"""Tests for durshift.analytics.duration_accounting."""

from __future__ import annotations

import pandas as pd

from durshift.analytics.duration_accounting import (
    build_bucketed_redistribution_summary,
    compute_nearby_gross_issuance,
    compute_retired_duration,
)


def _make_operations() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "operation_date": ["2025-03-05", "2025-03-05", "2025-03-19"],
            "cusip": ["AAA", "BBB", "CCC"],
            "par_amount_accepted": [1_000_000, 2_000_000, 3_000_000],
            "modified_duration": [4.5, 6.0, 8.0],
            "dv01": [450.0, 1200.0, 2400.0],
            "duration_dollars": [4_500_000, 12_000_000, 24_000_000],
            "maturity_bucket": ["2-5Y", "5-10Y", "10-20Y"],
            "purpose_label": ["cash_management", "liquidity_support", "liquidity_support"],
            "coupon_rate": [0.03, 0.04, 0.045],
            "yield_proxy": [0.04, 0.04, 0.04],
            "maturity_years": [3.0, 7.0, 15.0],
            "security_type": ["Note", "Note", "Bond"],
        }
    )


def _make_auctions() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "auction_date": ["2025-03-03", "2025-03-10", "2025-03-25"],
            "security_type": ["Bill", "Note", "Bond"],
            "offering_amt": ["50000000000", "25000000000", "15000000000"],
            "maturity_date": ["2025-06-03", "2027-03-10", "2045-03-25"],
        }
    )


# ── compute_retired_duration ────────────────────────────────────────


def test_retired_duration_groups_by_purpose_and_bucket():
    ops = _make_operations()
    result = compute_retired_duration(ops)

    assert isinstance(result, pd.DataFrame)
    assert "purpose_label" in result.columns
    assert "maturity_bucket" in result.columns
    # 3 rows: cash_management/2-5Y, liquidity_support/5-10Y, liquidity_support/10-20Y
    assert len(result) == 3


def test_retired_duration_aggregation_values():
    ops = _make_operations()
    result = compute_retired_duration(ops)

    # The liquidity_support / 5-10Y bucket has 1 security with par 2M
    row = result[
        (result["purpose_label"] == "liquidity_support") & (result["maturity_bucket"] == "5-10Y")
    ].iloc[0]
    assert row["n_securities"] == 1
    assert row["par_retired"] == 2_000_000
    assert row["total_duration_dollars"] == 12_000_000


def test_retired_duration_uses_accepted_amount_fallback():
    ops = _make_operations().rename(columns={"par_amount_accepted": "accepted_amount"})
    result = compute_retired_duration(ops)
    # Should still work with the alternative column name
    assert "par_retired" in result.columns
    assert result["par_retired"].sum() == 6_000_000


# ── build_bucketed_redistribution_summary ───────────────────────────


def test_bucketed_summary_has_percentage_columns():
    ops = _make_operations()
    result = build_bucketed_redistribution_summary(ops)

    assert "pct_par" in result.columns
    assert "pct_duration" in result.columns
    # Percentages should sum to 100
    assert abs(result["pct_par"].sum() - 100.0) < 0.5
    assert abs(result["pct_duration"].sum() - 100.0) < 0.5


def test_bucketed_summary_bucket_count():
    ops = _make_operations()
    result = build_bucketed_redistribution_summary(ops)
    # 3 distinct maturity buckets
    assert len(result) == 3


def test_bucketed_summary_par_totals():
    ops = _make_operations()
    result = build_bucketed_redistribution_summary(ops)
    assert result["par_retired"].sum() == 6_000_000


# ── compute_nearby_gross_issuance ────────────────────────────────────


def test_replacement_issuance_basic():
    ops = _make_operations()
    auctions = _make_auctions()
    result = compute_nearby_gross_issuance(auctions, ops, window_days=14)

    assert isinstance(result, pd.DataFrame)
    assert "operation_date" in result.columns
    assert "total_issuance" in result.columns
    # Two unique operation dates
    assert len(result) == 2


def test_replacement_issuance_window_matching():
    ops = _make_operations()
    auctions = _make_auctions()
    # Narrow window: only auctions within 3 days
    result = compute_nearby_gross_issuance(auctions, ops, window_days=3)

    # For 2025-03-05 op: auction on 2025-03-03 is within 3 days
    row_0305 = result[result["operation_date"] == pd.Timestamp("2025-03-05")].iloc[0]
    assert row_0305["n_nearby_auctions"] >= 1

    # For 2025-03-19 op: no auction within 3 days
    row_0319 = result[result["operation_date"] == pd.Timestamp("2025-03-19")].iloc[0]
    assert row_0319["n_nearby_auctions"] == 0


def test_replacement_issuance_security_type_breakdown():
    ops = _make_operations()
    auctions = _make_auctions()
    result = compute_nearby_gross_issuance(auctions, ops, window_days=14)

    assert "issuance_bill" in result.columns
    assert "issuance_note" in result.columns
    assert "issuance_bond" in result.columns


def test_replacement_issuance_avg_maturity():
    ops = _make_operations()
    auctions = _make_auctions()
    result = compute_nearby_gross_issuance(auctions, ops, window_days=14)

    # First operation date matches auctions with maturity_date info
    row = result.iloc[0]
    if "avg_replacement_maturity_years" in result.columns:
        assert row["avg_replacement_maturity_years"] > 0

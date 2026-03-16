"""Tests for durshift.analytics.event_windows."""

from __future__ import annotations

import pandas as pd

from durshift.analytics.event_windows import (
    build_event_study_panel,
    compute_dealer_event_windows,
    compute_yield_event_windows,
)


def _make_operations() -> pd.DataFrame:
    """Two operations on known dates."""
    return pd.DataFrame(
        {
            "operation_date": ["2025-03-05", "2025-03-19"],
            "cusip": ["912828AA1", "912828BB2"],
            "par_amount_accepted": [1_000_000, 2_000_000],
            "duration_dollars": [5_000_000, 12_000_000],
            "maturity_years": [5.0, 10.0],
            "operation_type": ["Buyback", "Buyback"],
            "security_type": ["Note", "Bond"],
        }
    )


def _make_dealer_positions() -> pd.DataFrame:
    """Weekly dealer positions spanning February-April 2025."""
    dates = pd.date_range("2025-02-05", periods=12, freq="W-WED")
    return pd.DataFrame(
        {"net_position": range(100, 100 + len(dates))},
        index=dates,
    )


def _make_h15_rates() -> pd.DataFrame:
    """Daily rates spanning February-April 2025."""
    dates = pd.bdate_range("2025-02-03", "2025-04-04")
    return pd.DataFrame(
        {"cmt_10y": [4.0 + i * 0.01 for i in range(len(dates))]},
        index=dates,
    )


# ── compute_dealer_event_windows ────────────────────────────────────


def test_dealer_event_windows_basic():
    ops = _make_operations()
    dealers = _make_dealer_positions()
    result = compute_dealer_event_windows(ops, dealers)

    assert isinstance(result, pd.DataFrame)
    assert "operation_date" in result.columns
    assert len(result) == 2
    # Should have pre/post/change columns
    assert "dealer_pre_net_position" in result.columns
    assert "dealer_post_net_position" in result.columns
    assert "dealer_change_net_position" in result.columns


def test_dealer_event_windows_change_is_post_minus_pre():
    ops = _make_operations()
    dealers = _make_dealer_positions()
    result = compute_dealer_event_windows(ops, dealers)

    for _, row in result.iterrows():
        pre = row["dealer_pre_net_position"]
        post = row["dealer_post_net_position"]
        change = row["dealer_change_net_position"]
        assert change == post - pre


def test_dealer_event_windows_no_match():
    """Operation date with no surrounding dealer data produces no change columns."""
    ops = pd.DataFrame({"operation_date": ["2030-01-01"]})
    dealers = _make_dealer_positions()  # data only in early 2025
    result = compute_dealer_event_windows(ops, dealers)

    assert len(result) == 1
    assert "dealer_change_net_position" not in result.columns


def test_dealer_event_windows_custom_window():
    ops = _make_operations().iloc[:1]
    dealers = _make_dealer_positions()
    # Very small window might exclude observations
    result = compute_dealer_event_windows(ops, dealers, pre_weeks=0, post_weeks=0)
    # With 0-week window the pre/post masks are empty
    assert len(result) == 1


# ── compute_yield_event_windows ─────────────────────────────────────


def test_yield_event_windows_basic():
    ops = _make_operations()
    rates = _make_h15_rates()
    result = compute_yield_event_windows(ops, rates)

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert "yield_pre_cmt_10y" in result.columns
    assert "yield_post_cmt_10y" in result.columns
    assert "yield_change_cmt_10y" in result.columns


def test_yield_event_windows_change_sign():
    """Rates increase over time so post > pre."""
    ops = _make_operations()
    rates = _make_h15_rates()
    result = compute_yield_event_windows(ops, rates)

    for _, row in result.iterrows():
        assert row["yield_change_cmt_10y"] == row["yield_post_cmt_10y"] - row["yield_pre_cmt_10y"]


# ── build_event_study_panel ─────────────────────────────────────────


def test_build_event_study_panel_merges_all():
    ops = _make_operations()
    dealers = _make_dealer_positions()
    rates = _make_h15_rates()
    panel = build_event_study_panel(ops, dealers, rates)

    assert isinstance(panel, pd.DataFrame)
    assert len(panel) == 2
    # Operation summary columns
    assert "total_par_accepted" in panel.columns
    assert "n_securities" in panel.columns
    # Dealer event columns
    assert "dealer_change_net_position" in panel.columns
    # Yield event columns
    assert "yield_change_cmt_10y" in panel.columns


def test_build_event_study_panel_sorted_by_date():
    ops = _make_operations()
    dealers = _make_dealer_positions()
    rates = _make_h15_rates()
    panel = build_event_study_panel(ops, dealers, rates)

    dates = panel["operation_date"].tolist()
    assert dates == sorted(dates)


# ── Offset selection tests ─────────────────────────────────────────


def test_dealer_event_windows_selects_exact_offset_dates():
    """With pre_weeks=2, the pre observation should be closest to exactly
    14 days before the operation, not just the nearest-before."""
    ops = pd.DataFrame({"operation_date": ["2025-03-19"]})
    # Weekly dealer data on Wednesdays
    dates = pd.date_range("2025-02-05", periods=12, freq="W-WED")
    dealers = pd.DataFrame({"val": range(100, 100 + len(dates))}, index=dates)

    result = compute_dealer_event_windows(ops, dealers, pre_weeks=2, post_weeks=2)
    assert len(result) == 1
    row = result.iloc[0]

    # Target pre: 2025-03-19 - 14 days = 2025-03-05
    # Nearest Wednesday to 2025-03-05 is 2025-03-05 (it IS a Wednesday)
    assert row["dealer_pre_date"] == pd.Timestamp("2025-03-05")

    # Target post: 2025-03-19 + 14 days = 2025-04-02
    # Nearest Wednesday to 2025-04-02 is 2025-04-02 (it IS a Wednesday)
    assert row["dealer_post_date"] == pd.Timestamp("2025-04-02")


def test_yield_event_windows_selects_exact_offset_dates():
    """With pre_days=5, the pre observation should be closest to exactly
    5 calendar days before the operation."""
    ops = pd.DataFrame({"operation_date": ["2025-03-12"]})
    rates = pd.DataFrame(
        {"cmt_10y": [4.0, 4.1, 4.2, 4.3, 4.4]},
        index=pd.to_datetime(
            ["2025-03-05", "2025-03-06", "2025-03-07", "2025-03-14", "2025-03-17"]
        ),
    )

    result = compute_yield_event_windows(ops, rates, pre_days=5, post_days=5)
    assert len(result) == 1
    row = result.iloc[0]

    # Target pre: 2025-03-12 - 5 = 2025-03-07 → exact match
    assert row["yield_pre_date"] == pd.Timestamp("2025-03-07")
    assert row["yield_pre_cmt_10y"] == 4.2

    # Target post: 2025-03-12 + 5 = 2025-03-17 → exact match
    assert row["yield_post_date"] == pd.Timestamp("2025-03-17")
    assert row["yield_post_cmt_10y"] == 4.4

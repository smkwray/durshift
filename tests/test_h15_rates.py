"""Tests for durshift.data.h15_rates.interpolate_yield_for_maturity."""

from __future__ import annotations

import pandas as pd

from durshift.data.h15_rates import interpolate_yield_for_maturity


def _make_rates() -> pd.DataFrame:
    """Small synthetic H.15 rates DataFrame with three dates."""
    dates = pd.to_datetime(["2025-03-03", "2025-03-04", "2025-03-05"])
    return pd.DataFrame(
        {
            "cmt_1m": [5.30, 5.31, 5.32],
            "cmt_3m": [5.20, 5.21, 5.22],
            "cmt_6m": [5.00, 5.01, 5.02],
            "cmt_1y": [4.70, 4.71, 4.72],
            "cmt_2y": [4.30, 4.31, 4.32],
            "cmt_3y": [4.20, 4.21, 4.22],
            "cmt_5y": [4.10, 4.11, 4.12],
            "cmt_7y": [4.15, 4.16, 4.17],
            "cmt_10y": [4.25, 4.26, 4.27],
            "cmt_20y": [4.50, 4.51, 4.52],
            "cmt_30y": [4.45, 4.46, 4.47],
        },
        index=dates,
    )


# ── Exact tenor match ───────────────────────────────────────────────


def test_exact_tenor_10y():
    rates = _make_rates()
    result = interpolate_yield_for_maturity(rates, pd.Timestamp("2025-03-04"), 10.0)
    # 10Y rate on 2025-03-04 is 4.26 -> result should be 4.26 / 100
    assert result is not None
    assert abs(result - 4.26 / 100) < 1e-9


def test_exact_tenor_2y():
    rates = _make_rates()
    result = interpolate_yield_for_maturity(rates, pd.Timestamp("2025-03-03"), 2.0)
    assert result is not None
    assert abs(result - 4.30 / 100) < 1e-9


# ── Interpolation between tenors ────────────────────────────────────


def test_interpolation_between_5y_and_7y():
    rates = _make_rates()
    # 6Y should interpolate between 5Y (4.11) and 7Y (4.16) on 2025-03-04
    result = interpolate_yield_for_maturity(rates, pd.Timestamp("2025-03-04"), 6.0)
    assert result is not None
    expected = (4.11 + 0.5 * (4.16 - 4.11)) / 100  # weight = (6-5)/(7-5) = 0.5
    assert abs(result - expected) < 1e-9


def test_interpolation_between_2y_and_3y():
    rates = _make_rates()
    # 2.5Y on 2025-03-05: between 2Y (4.32) and 3Y (4.22)
    result = interpolate_yield_for_maturity(rates, pd.Timestamp("2025-03-05"), 2.5)
    assert result is not None
    expected = (4.32 + 0.5 * (4.22 - 4.32)) / 100
    assert abs(result - expected) < 1e-9


# ── Date not in index (nearest match) ───────────────────────────────


def test_nearest_date_used_when_not_in_index():
    rates = _make_rates()
    # 2025-03-06 is not in the index; nearest is 2025-03-05 (1 day away)
    result = interpolate_yield_for_maturity(rates, pd.Timestamp("2025-03-06"), 10.0)
    assert result is not None
    assert abs(result - 4.27 / 100) < 1e-9


def test_date_too_far_returns_none():
    rates = _make_rates()
    # 2025-03-20 is more than 5 days from any index date
    result = interpolate_yield_for_maturity(rates, pd.Timestamp("2025-03-20"), 10.0)
    assert result is None


# ── Maturity beyond 30Y ─────────────────────────────────────────────


def test_maturity_beyond_30y_returns_30y_rate():
    rates = _make_rates()
    # 40Y is beyond max tenor; function should return the 30Y rate (below only)
    result = interpolate_yield_for_maturity(rates, pd.Timestamp("2025-03-04"), 40.0)
    assert result is not None
    # above is None -> returns below[1] / 100 = 4.46 / 100
    assert abs(result - 4.46 / 100) < 1e-9


# ── Maturity below 1M ───────────────────────────────────────────────


def test_maturity_below_minimum_returns_shortest_rate():
    rates = _make_rates()
    # 0.01Y is below 1M tenor; below is None -> returns above[1] / 100
    result = interpolate_yield_for_maturity(rates, pd.Timestamp("2025-03-04"), 0.01)
    assert result is not None
    # above is 1M (5.31) -> 5.31 / 100
    assert abs(result - 5.31 / 100) < 1e-9

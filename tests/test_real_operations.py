"""Tests for durshift.panels.real_operations helpers."""

from __future__ import annotations

import pandas as pd

from durshift.panels.real_operations import _resolve_yield, _safe_duration, _safe_dv01


def _make_h15() -> pd.DataFrame:
    """Small H.15 rates with one date."""
    dates = pd.to_datetime(["2025-03-05"])
    return pd.DataFrame(
        {
            "cmt_1m": [5.30],
            "cmt_3m": [5.20],
            "cmt_6m": [5.00],
            "cmt_1y": [4.70],
            "cmt_2y": [4.30],
            "cmt_3y": [4.20],
            "cmt_5y": [4.10],
            "cmt_7y": [4.15],
            "cmt_10y": [4.25],
            "cmt_20y": [4.50],
            "cmt_30y": [4.45],
        },
        index=dates,
    )


# ── _resolve_yield ────────────────────────────────────────────


def test_resolve_yield_uses_h15():
    h15 = _make_h15()
    row = pd.Series(
        {
            "operation_date": pd.Timestamp("2025-03-05"),
            "maturity_years": 10.0,
            "coupon_rate": 0.03,
            "security_type": "Nominal Coupons",
        }
    )
    result = _resolve_yield(h15, None, row)
    # Should come from H.15 interpolation (4.25 / 100 = 0.0425)
    assert abs(result - 0.0425) < 1e-6


def test_resolve_yield_fallback_to_coupon():
    h15 = _make_h15()
    # Date not in H.15 and too far from any index date
    row = pd.Series(
        {
            "operation_date": pd.Timestamp("2025-06-01"),
            "maturity_years": 10.0,
            "coupon_rate": 0.03,
            "security_type": "Nominal Coupons",
        }
    )
    result = _resolve_yield(h15, None, row)
    # interpolate_yield_for_maturity returns None -> falls back to coupon
    assert abs(result - 0.03) < 1e-9


def test_resolve_yield_nan_maturity():
    h15 = _make_h15()
    row = pd.Series(
        {
            "operation_date": pd.Timestamp("2025-03-05"),
            "maturity_years": float("nan"),
            "coupon_rate": 0.04,
            "security_type": "Nominal Coupons",
        }
    )
    result = _resolve_yield(h15, None, row)
    # NaN maturity -> falls back to coupon (clipped to min 0.005)
    assert abs(result - 0.04) < 1e-9


def test_resolve_yield_zero_coupon_floor():
    h15 = _make_h15()
    row = pd.Series(
        {
            "operation_date": pd.Timestamp("2025-06-01"),
            "maturity_years": float("nan"),
            "coupon_rate": 0.0,
            "security_type": "Nominal Coupons",
        }
    )
    result = _resolve_yield(h15, None, row)
    # max(0.0, 0.005) = 0.005
    assert abs(result - 0.005) < 1e-9


# ── _safe_duration ──────────────────────────────────────────────────


def test_safe_duration_positive():
    result = _safe_duration(0.04, 0.04, 10.0)
    assert result > 0
    assert result < 15  # reasonable for a 10Y


def test_safe_duration_zero_maturity():
    result = _safe_duration(0.04, 0.04, 0.0)
    assert result == 0.0


def test_safe_duration_negative_maturity():
    result = _safe_duration(0.04, 0.04, -1.0)
    assert result == 0.0


def test_safe_duration_nan_maturity():
    result = _safe_duration(0.04, 0.04, float("nan"))
    assert result == 0.0


# ── _safe_dv01 ──────────────────────────────────────────────────────


def test_safe_dv01_positive():
    result = _safe_dv01(1_000_000, 0.04, 0.04, 10.0)
    assert result > 0


def test_safe_dv01_zero_maturity():
    result = _safe_dv01(1_000_000, 0.04, 0.04, 0.0)
    assert result == 0.0


def test_safe_dv01_nan_maturity():
    result = _safe_dv01(1_000_000, 0.04, 0.04, float("nan"))
    assert result == 0.0


def test_safe_dv01_scales_with_par():
    """DV01 should scale linearly with par amount."""
    dv01_1m = _safe_dv01(1_000_000, 0.04, 0.04, 5.0)
    dv01_2m = _safe_dv01(2_000_000, 0.04, 0.04, 5.0)
    assert abs(dv01_2m - 2 * dv01_1m) < 1e-6

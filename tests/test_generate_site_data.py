"""CI smoke test for scripts/generate_site_data.py::generate_all."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd

# scripts/ is not a package — add to sys.path so we can import directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from generate_site_data import generate_all  # noqa: E402

# ── helpers ────────────────────────────────────────────────────────────


def _make_operations() -> pd.DataFrame:
    """Minimal ops DataFrame with 6 rows across 2 operation dates."""
    return pd.DataFrame(
        {
            "operation_date": pd.to_datetime(
                [
                    "2025-03-05",
                    "2025-03-05",
                    "2025-03-05",
                    "2025-03-19",
                    "2025-03-19",
                    "2025-03-19",
                ]
            ),
            "cusip": [
                "912828AA1",
                "912828BB2",
                "912828CC3",
                "912828DD4",
                "912828EE5",
                "912828FF6",
            ],
            "par_amount_accepted": [
                1_500_000,
                2_000_000,
                3_000_000,
                2_500_000,
                1_800_000,
                4_200_000,
            ],
            "duration_dollars": [
                6_750_000,
                14_000_000,
                27_000_000,
                20_000_000,
                10_800_000,
                46_200_000,
            ],
            "maturity_years": [3.0, 7.0, 15.0, 8.0, 4.0, 22.0],
            "modified_duration": [2.8, 5.5, 10.5, 6.2, 3.5, 14.0],
            "yield_proxy": [0.042, 0.039, 0.041, 0.040, 0.043, 0.038],
            "operation_type": [
                "Buyback",
                "Buyback",
                "Buyback",
                "Buyback",
                "Buyback",
                "Buyback",
            ],
            "security_type": ["Note", "Note", "Bond", "Note", "Note", "Bond"],
            "maturity_bucket": ["2-5Y", "5-10Y", "10-20Y", "5-10Y", "2-5Y", "20Y+"],
            "coupon_rate": [0.025, 0.035, 0.045, 0.030, 0.028, 0.040],
            "purpose_label": [
                "cash_management",
                "liquidity_support",
                "liquidity_support",
                "cash_management",
                "cash_management",
                "liquidity_support",
            ],
            "dv01": [420.0, 1100.0, 3150.0, 1550.0, 630.0, 5880.0],
            "weighted_avg_price": [99.5, 98.0, 95.0, 97.5, 99.0, 92.0],
            "maturity_date": pd.to_datetime(
                ["2028-03-05", "2032-03-05", "2040-03-05", "2033-03-19", "2029-03-19", "2047-03-19"]
            ),
        }
    )


def _make_h15() -> pd.DataFrame:
    """Daily H.15 rates with 11 CMT tenors spanning the operation window."""
    dates = pd.bdate_range("2025-02-20", "2025-04-01")
    cols = [
        "cmt_1m",
        "cmt_3m",
        "cmt_6m",
        "cmt_1y",
        "cmt_2y",
        "cmt_3y",
        "cmt_5y",
        "cmt_7y",
        "cmt_10y",
        "cmt_20y",
        "cmt_30y",
    ]
    data = {}
    base_rates = [4.5, 4.4, 4.3, 4.2, 4.0, 3.95, 3.9, 3.88, 3.85, 4.0, 4.1]
    for col, base in zip(cols, base_rates, strict=True):
        data[col] = [base + i * 0.005 for i in range(len(dates))]
    return pd.DataFrame(data, index=dates)


def _make_dealers() -> pd.DataFrame:
    """Weekly dealer positions with 7 maturity-bucket columns."""
    dates = pd.date_range("2025-02-05", periods=12, freq="W-WED")
    cols = [
        "treasury_coupons_lt2y",
        "treasury_coupons_2_3y",
        "treasury_coupons_3_6y",
        "treasury_coupons_6_7y",
        "treasury_coupons_7_11y",
        "treasury_coupons_11_21y",
        "treasury_coupons_gt21y",
    ]
    data = {}
    for j, col in enumerate(cols):
        data[col] = [5_000_000 + i * 100_000 + j * 50_000 for i in range(len(dates))]
    return pd.DataFrame(data, index=dates)


# ── test ───────────────────────────────────────────────────────────────


def test_generate_all_produces_expected_json(tmp_path: Path) -> None:
    ops = _make_operations()
    h15 = _make_h15()
    dealers = _make_dealers()

    # Redirect the hard-coded DATA path so the CSV write goes to tmp_path
    fake_data = tmp_path / "data"
    (fake_data / "processed").mkdir(parents=True)

    with patch("generate_site_data.DATA", fake_data):
        generate_all(ops, h15, dealers, tmp_path, tables_dir=None)

    # ── file existence ────────────────────────────────────────────
    expected_files = [
        "operations.json",
        "duration_buckets.json",
        "yield_changes.json",
        "dealer_changes.json",
        "monthly_volume.json",
        "summary.json",
        "event_study.json",
    ]
    for fname in expected_files:
        assert (tmp_path / fname).exists(), f"Missing {fname}"

    # ── operations.json ───────────────────────────────────────────
    operations = json.loads((tmp_path / "operations.json").read_text())
    assert isinstance(operations, list)
    assert len(operations) >= 2
    for item in operations:
        assert "operation_date" in item
        assert "n_securities" in item
        assert "total_par" in item
        assert "total_duration_dollars" in item

    # ── yield_changes.json ────────────────────────────────────────
    yields = json.loads((tmp_path / "yield_changes.json").read_text())
    assert isinstance(yields, list)
    assert len(yields) > 0
    for item in yields:
        assert "tenor" in item
        assert "mean_bp" in item
        assert "median_bp" in item
        assert "std_err" in item
        assert "ci_lower" in item
        assert "ci_upper" in item
        assert "p_value" in item
        assert "significant" in item
        assert "n" in item
        # Type checks
        assert isinstance(item["p_value"], float)
        assert 0.0 <= item["p_value"] <= 1.0
        assert isinstance(item["significant"], bool)
        assert isinstance(item["n"], int)
        # CI constraint
        assert item["ci_lower"] <= item["mean_bp"] <= item["ci_upper"]

    # ── dealer_changes.json ───────────────────────────────────────
    dealers_out = json.loads((tmp_path / "dealer_changes.json").read_text())
    assert isinstance(dealers_out, list)
    assert len(dealers_out) > 0
    for item in dealers_out:
        assert "bucket" in item
        assert "mean_B" in item
        assert "median_B" in item
        assert "std_err" in item
        assert "ci_lower" in item
        assert "ci_upper" in item
        assert "p_value" in item
        assert "significant" in item
        assert "n" in item
        # Type checks
        assert isinstance(item["p_value"], float)
        assert 0.0 <= item["p_value"] <= 1.0
        assert isinstance(item["significant"], bool)
        assert isinstance(item["n"], int)

    # ── summary.json ──────────────────────────────────────────────
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert isinstance(summary, dict)
    assert "total_operations" in summary
    assert "total_par_B" in summary
    assert "total_duration_dollars_B" in summary
    assert "unique_cusips" in summary

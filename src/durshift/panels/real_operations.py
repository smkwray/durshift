"""Build the operation panel from real buyback results data.

Takes the security-level buyback results CSV (from buyback_results.py)
and produces an operation-level panel with derived fields for duration
analysis.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from durshift.analytics.classification import classify_operation
from durshift.analytics.duration import dv01, maturity_bucket, modified_duration
from durshift.utils.files import ensure_parent_dir

logger = logging.getLogger(__name__)

# Columns in the final operation panel.
REAL_PANEL_COLUMNS = [
    "operation_date",
    "settlement_date",
    "operation_type",
    "security_type",
    "maturity_bucket_label",
    "cusip",
    "coupon_rate",
    "maturity_date",
    "par_amount_accepted",
    "weighted_avg_price",
    "market_value",
    "maturity_years",
    "yield_proxy",
    "purpose_label",
    "maturity_bucket",
    "modified_duration",
    "dv01",
    "duration_dollars",
    "issues_eligible",
    "issues_accepted",
    "total_par_offered",
    "total_par_accepted",
    "yield_source",
]


def build_real_operation_panel(
    results_path: str | Path,
    h15_rates_path: str | Path | None = None,
    tips_yields_path: str | Path | None = None,
) -> pd.DataFrame:
    """Build analysis-ready panel from buyback results CSV.

    Parameters
    ----------
    results_path : str | Path
        Path to the security-level CSV produced by buyback_results.py.
    h15_rates_path : str | Path | None
        Optional path to H.15 rates CSV for nominal yield proxies.
    tips_yields_path : str | Path | None
        Optional path to TIPS real yields CSV. If provided, TIPS securities
        use real yields instead of nominal.

    Returns
    -------
    pd.DataFrame
        One row per accepted security per operation with derived analytics fields.
    """
    raw = pd.read_csv(results_path)
    logger.info("Loaded %d security rows from %s", len(raw), results_path)

    # Load H.15 nominal rates if available
    h15 = None
    if h15_rates_path is not None:
        h15 = pd.read_csv(h15_rates_path, index_col=0, parse_dates=True)
        logger.info("Loaded H.15 rates (%d obs) for nominal yield proxies", len(h15))

    # Load TIPS real yields if available
    tips_rates = None
    if tips_yields_path is not None:
        from durshift.data.h15_rates import load_tips_real_yields

        tips_rates = load_tips_real_yields(tips_yields_path)
        logger.info("Loaded TIPS real yields (%d obs) for TIPS yield proxies", len(tips_rates))

    # Convert types
    raw["operation_date"] = pd.to_datetime(raw["operation_date"], format="mixed")
    raw["settlement_date"] = pd.to_datetime(raw["settlement_date"], errors="coerce")
    raw["maturity_date"] = pd.to_datetime(raw["maturity_date"], errors="coerce")

    for col in [
        "par_amount_accepted",
        "weighted_avg_price",
        "coupon_rate",
        "total_par_offered",
        "total_par_accepted",
        "issues_eligible",
        "issues_accepted",
    ]:
        raw[col] = pd.to_numeric(raw[col], errors="coerce")

    # Filter to securities with non-zero accepted amounts
    panel = raw[raw["par_amount_accepted"] > 0].copy()
    logger.info("Filtered to %d accepted securities", len(panel))

    # Derive maturity_years from operation_date and maturity_date
    panel["maturity_years"] = (panel["maturity_date"] - panel["operation_date"]).dt.days / 365.25

    # Coupon rate: convert from percent to decimal
    panel["coupon_rate"] = panel["coupon_rate"] / 100.0

    # Yield proxy: TIPS get real yields, nominals get nominal CMT
    if h15 is not None or tips_rates is not None:
        results = panel.apply(
            lambda row: _resolve_yield(h15, tips_rates, row),
            axis=1,
        )
        panel["yield_proxy"] = results.apply(lambda x: x[0])
        panel["yield_source"] = results.apply(lambda x: x[1])
    else:
        panel["yield_proxy"] = panel["coupon_rate"].clip(lower=0.005)
        panel["yield_source"] = "coupon"

    # Purpose label
    panel["purpose_label"] = panel.apply(
        lambda row: classify_operation(
            security_type=str(row["security_type"]),
            maturity_years=float(row["maturity_years"]) if pd.notna(row["maturity_years"]) else 5.0,
            stated_purpose=str(row["operation_type"]),
        ),
        axis=1,
    )

    # Maturity bucket (DurShift standard 5 buckets)
    panel["maturity_bucket"] = panel["maturity_years"].apply(
        lambda y: maturity_bucket(float(y)) if pd.notna(y) else "unknown"
    )

    # Duration and DV01
    panel["modified_duration"] = panel.apply(
        lambda row: _safe_duration(row["coupon_rate"], row["yield_proxy"], row["maturity_years"]),
        axis=1,
    )
    panel["dv01"] = panel.apply(
        lambda row: _safe_dv01(
            row["par_amount_accepted"],
            row["coupon_rate"],
            row["yield_proxy"],
            row["maturity_years"],
        ),
        axis=1,
    )
    # Market-value-weighted duration: (par * price/100) * modified_duration
    # This is true dollar-duration, not par-weighted duration-years.
    # Fall back to par (price=100) when weighted_avg_price is NaN.
    price = panel["weighted_avg_price"].fillna(100.0)
    panel["market_value"] = panel["par_amount_accepted"] * price / 100.0
    panel["duration_dollars"] = panel["market_value"] * panel["modified_duration"]

    # Rename for clarity
    panel = panel.rename(columns={"maturity_bucket_x": "maturity_bucket_label"})
    if "maturity_bucket_label" not in panel.columns:
        panel["maturity_bucket_label"] = panel["maturity_bucket"]

    # Reorder and select final columns (only those that exist)
    final_cols = [c for c in REAL_PANEL_COLUMNS if c in panel.columns]
    panel = panel[final_cols].sort_values("operation_date").reset_index(drop=True)

    logger.info("Built real operation panel: %d rows, %d columns", len(panel), len(panel.columns))
    return panel


def build_and_save_real_panel(
    results_path: str | Path,
    output_path: str | Path,
    h15_rates_path: str | Path | None = None,
    tips_yields_path: str | Path | None = None,
) -> Path:
    """Build the real operation panel and save as CSV."""
    panel = build_real_operation_panel(
        results_path,
        h15_rates_path=h15_rates_path,
        tips_yields_path=tips_yields_path,
    )
    out = ensure_parent_dir(output_path)
    panel.to_csv(out, index=False)
    logger.info("Saved real operation panel to %s", out)
    return out


def _resolve_yield(
    h15: pd.DataFrame | None,
    tips_rates: pd.DataFrame | None,
    row: pd.Series,
) -> tuple[float, str]:
    """Pick the right yield curve (nominal or TIPS real) and interpolate."""
    from durshift.data.h15_rates import interpolate_tips_yield, interpolate_yield_for_maturity

    mat_years = row.get("maturity_years")
    op_date = row.get("operation_date")
    sec_type = str(row.get("security_type", "")).upper()
    coupon_fallback = max(float(row.get("coupon_rate", 0.005)), 0.005)

    if pd.isna(mat_years) or pd.isna(op_date):
        return (coupon_fallback, "coupon")

    ts = pd.Timestamp(op_date)

    # TIPS securities: use real yield curve (which CAN be negative)
    if "TIPS" in sec_type and tips_rates is not None:
        rate = interpolate_tips_yield(tips_rates, ts, float(mat_years))
        if rate is not None:
            # Real yields can be negative; floor at -0.05 to avoid degenerate math
            return (max(rate, -0.05), "tips_real")

    # Nominal securities (or TIPS fallback): use nominal CMT
    if h15 is not None:
        rate = interpolate_yield_for_maturity(h15, ts, float(mat_years))
        if rate is not None and rate > 0:
            return (rate, "h15_nominal")

    return (coupon_fallback, "coupon")


def _safe_duration(coupon_rate, yield_rate, maturity_years) -> float:
    """Modified duration with fallback for edge cases."""
    try:
        if pd.isna(maturity_years) or maturity_years <= 0:
            return 0.0
        return modified_duration(
            coupon_rate=float(coupon_rate),
            yield_rate=float(yield_rate),
            maturity_years=float(maturity_years),
        )
    except (ValueError, ZeroDivisionError):
        return 0.0


def _safe_dv01(par_amount, coupon_rate, yield_rate, maturity_years) -> float:
    """DV01 with fallback for edge cases."""
    try:
        if pd.isna(maturity_years) or maturity_years <= 0:
            return 0.0
        return dv01(
            par_amount=float(par_amount),
            coupon_rate=float(coupon_rate),
            yield_rate=float(yield_rate),
            maturity_years=float(maturity_years),
        )
    except (ValueError, ZeroDivisionError):
        return 0.0

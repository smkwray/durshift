"""Generate all JSON data files consumed by the static site.

Run after rebuilding the operation panel and fetching all data sources:
    python -B scripts/generate_site_data.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from scipy import stats as sp_stats

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "site" / "public" / "data"
OUT.mkdir(parents=True, exist_ok=True)


def generate_all(
    ops: pd.DataFrame,
    h15: pd.DataFrame,
    dealers: pd.DataFrame,
    out_dir: Path,
    tables_dir: Path | None = ROOT / "outputs" / "tables",
) -> None:
    """Core generation logic.  Accepts pre-loaded DataFrames so tests can call
    this without touching the filesystem for input data."""

    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. operations.json
    op_summary = (
        ops.groupby("operation_date")
        .agg(
            n_securities=("cusip", "count"),
            total_par=("par_amount_accepted", "sum"),
            total_duration_dollars=("duration_dollars", "sum"),
            avg_maturity=("maturity_years", "mean"),
            avg_duration=("modified_duration", "mean"),
            avg_yield=("yield_proxy", "mean"),
            operation_types=("operation_type", lambda x: "|".join(sorted(x.unique()))),
            security_types=("security_type", lambda x: "|".join(sorted(x.unique()))),
        )
        .reset_index()
    )
    op_summary["operation_date"] = op_summary["operation_date"].dt.strftime("%Y-%m-%d")
    op_summary.to_json(out_dir / "operations.json", orient="records", indent=2, date_format="iso")
    print(f"operations.json: {len(op_summary)} records")

    # 2. duration_buckets.json
    from durshift.analytics.duration_accounting import build_bucketed_redistribution_summary

    bucket = build_bucketed_redistribution_summary(ops)
    # Sort by maturity order, not alphabetical
    bucket_order = ["0-2Y", "2-5Y", "5-10Y", "10-20Y", "20Y+"]
    bucket["_sort"] = bucket["maturity_bucket"].map({b: i for i, b in enumerate(bucket_order)})
    bucket = bucket.sort_values("_sort").drop(columns=["_sort"])
    bucket.to_json(out_dir / "duration_buckets.json", orient="records", indent=2, date_format="iso")
    print(f"duration_buckets.json: {len(bucket)} records")

    # 3. event_study + yield/dealer changes
    from durshift.analytics.event_windows import build_event_study_panel

    events = build_event_study_panel(ops, dealers, h15)
    events_out = events.copy()
    for col in events_out.columns:
        if pd.api.types.is_datetime64_any_dtype(events_out[col]):
            events_out[col] = events_out[col].dt.strftime("%Y-%m-%d")
    events_out.to_json(out_dir / "event_study.json", orient="records", indent=2, date_format="iso")
    events_out.to_csv(DATA / "processed" / "event_study_panel.csv", index=False)
    print(f"event_study.json: {len(events_out)} records")

    # 4. monthly_volume.json
    ops_monthly = (
        ops.set_index("operation_date")
        .resample("ME")
        .agg(
            total_par=("par_amount_accepted", "sum"),
            total_duration=("duration_dollars", "sum"),
            n_operations=("cusip", "count"),
        )
        .reset_index()
    )
    ops_monthly["operation_date"] = ops_monthly["operation_date"].dt.strftime("%Y-%m")
    ops_monthly.to_json(
        out_dir / "monthly_volume.json", orient="records", indent=2, date_format="iso"
    )
    print(f"monthly_volume.json: {len(ops_monthly)} records")

    # 5. yield_changes.json
    yield_cols = [
        "yield_change_cmt_1m",
        "yield_change_cmt_3m",
        "yield_change_cmt_6m",
        "yield_change_cmt_1y",
        "yield_change_cmt_2y",
        "yield_change_cmt_3y",
        "yield_change_cmt_5y",
        "yield_change_cmt_7y",
        "yield_change_cmt_10y",
        "yield_change_cmt_20y",
        "yield_change_cmt_30y",
    ]
    tenor_labels = ["1M", "3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "20Y", "30Y"]
    yield_data = []
    for col, label in zip(yield_cols, tenor_labels, strict=True):
        if col in events.columns:
            vals = events[col].dropna().astype(float) * 100
            n = len(vals)
            mean = vals.mean()
            std_err = vals.std() / n**0.5 if n > 1 else 0.0
            _, p_value = sp_stats.ttest_1samp(vals, 0) if n > 1 else (0, 1.0)
            yield_data.append(
                {
                    "tenor": label,
                    "mean_bp": round(float(mean), 2),
                    "median_bp": round(float(vals.median()), 2),
                    "std_err": round(float(std_err), 3),
                    "ci_lower": round(float(mean - 1.96 * std_err), 2),
                    "ci_upper": round(float(mean + 1.96 * std_err), 2),
                    "p_value": round(float(p_value), 4),
                    "significant": bool(p_value < 0.05),
                    "n": n,
                }
            )
    _write_json(out_dir / "yield_changes.json", yield_data)
    print(f"yield_changes.json: {len(yield_data)} records")

    # 6. dealer_changes.json
    dealer_map = {
        "dealer_change_treasury_coupons_lt2y": "<2Y",
        "dealer_change_treasury_coupons_2_3y": "2-3Y",
        "dealer_change_treasury_coupons_3_6y": "3-6Y",
        "dealer_change_treasury_coupons_6_7y": "6-7Y",
        "dealer_change_treasury_coupons_7_11y": "7-11Y",
        "dealer_change_treasury_coupons_11_21y": "11-21Y",
        "dealer_change_treasury_coupons_gt21y": ">21Y",
    }
    dealer_data = []
    for col, label in dealer_map.items():
        if col in events.columns:
            vals = events[col].dropna().astype(float) / 1e3
            n = len(vals)
            mean = vals.mean()
            std_err = vals.std() / n**0.5 if n > 1 else 0.0
            _, p_value = sp_stats.ttest_1samp(vals, 0) if n > 1 else (0, 1.0)
            dealer_data.append(
                {
                    "bucket": label,
                    "mean_B": round(float(mean), 2),
                    "median_B": round(float(vals.median()), 2),
                    "std_err": round(float(std_err), 3),
                    "ci_lower": round(float(mean - 1.96 * std_err), 2),
                    "ci_upper": round(float(mean + 1.96 * std_err), 2),
                    "p_value": round(float(p_value), 4),
                    "significant": bool(p_value < 0.05),
                    "n": n,
                }
            )
    _write_json(out_dir / "dealer_changes.json", dealer_data)
    print(f"dealer_changes.json: {len(dealer_data)} records")

    # 7. soma_context.json
    soma_path = DATA / "raw" / "soma_holdings.csv"
    if soma_path.exists():
        soma = pd.read_csv(soma_path, index_col=0, parse_dates=True)
        # Monthly resample for the site chart
        soma_monthly = soma.resample("ME").last().dropna(how="all")
        soma_site = []
        for date, row in soma_monthly.iterrows():
            entry = {"date": date.strftime("%Y-%m")}
            for c in ["total", "bills", "notes_bonds", "tips", "frn", "mbs"]:
                if c in row.index:
                    entry[c] = round(row[c] / 1e9, 1) if pd.notna(row[c]) else None
            soma_site.append(entry)
        _write_json(out_dir / "soma.json", soma_site)
        print(f"soma.json: {len(soma_site)} records")

    # 8. summary.json
    summary = {
        "total_operations": int(ops["cusip"].count()),
        "total_operation_dates": int(ops["operation_date"].nunique()),
        "total_par_B": round(ops["par_amount_accepted"].sum() / 1e9, 1),
        "total_duration_dollars_B": round(ops["duration_dollars"].sum() / 1e9, 1),
        "unique_cusips": int(ops["cusip"].nunique()),
        "date_range_start": op_summary["operation_date"].min(),
        "date_range_end": op_summary["operation_date"].max(),
    }
    _write_json(out_dir / "summary.json", summary)
    print(f"summary.json: dur_dollars={summary['total_duration_dollars_B']}B")

    # 9. Regenerate output tables
    if tables_dir is not None:
        tables_dir.mkdir(parents=True, exist_ok=True)
        bucket.to_csv(tables_dir / "duration_redistribution_summary.csv", index=False)

        from durshift.reporting.summary_tables import build_duration_summary

        dur_summary = build_duration_summary(ops)
        dur_summary.to_csv(tables_dir / "real_duration_summary.csv", index=False)
        print("Output tables regenerated")


def main() -> None:
    ops = pd.read_csv(DATA / "processed" / "real_operation_panel.csv")
    ops["operation_date"] = pd.to_datetime(ops["operation_date"])
    h15 = pd.read_csv(DATA / "raw" / "h15_rates.csv", index_col=0, parse_dates=True)
    dealers = pd.read_csv(DATA / "raw" / "dealer_positions.csv", index_col=0, parse_dates=True)
    generate_all(ops, h15, dealers, OUT)


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

"""Duration-redistribution accounting.

Quantifies what duration is retired via buybacks and what duration is
replaced via new issuance. The core question: does Treasury buyback
activity shift the maturity/duration composition of outstanding debt?
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def compute_retired_duration(operations: pd.DataFrame) -> pd.DataFrame:
    """Summarize retired duration by maturity bucket and purpose.

    Parameters
    ----------
    operations : pd.DataFrame
        Real operation panel with par_amount_accepted, modified_duration,
        duration_dollars, maturity_bucket, purpose_label columns.

    Returns
    -------
    pd.DataFrame
        Aggregated retired duration by bucket and purpose.
    """
    amount_col = (
        "par_amount_accepted" if "par_amount_accepted" in operations.columns else "accepted_amount"
    )

    summary = (
        operations.groupby(["purpose_label", "maturity_bucket"])
        .agg(
            n_securities=("cusip", "count"),
            par_retired=(amount_col, "sum"),
            avg_modified_duration=("modified_duration", "mean"),
            avg_dv01=("dv01", "mean"),
            total_duration_dollars=("duration_dollars", "sum"),
        )
        .reset_index()
        .sort_values(["purpose_label", "maturity_bucket"])
    )

    logger.info("Computed retired duration: %d bucket-purpose combinations", len(summary))
    return summary


def compute_nearby_gross_issuance(
    auctions: pd.DataFrame,
    operations: pd.DataFrame,
    *,
    window_days: int = 14,
) -> pd.DataFrame:
    """Compute gross auction issuance near each buyback operation.

    For each buyback operation date, finds all auctions within +/- window_days
    and sums their offering amounts. This is *gross nearby issuance*, not
    matched replacement supply: bills dominate auction cadence and inflate
    the totals. Use for context, not as a direct replacement measure.

    Parameters
    ----------
    auctions : pd.DataFrame
        Auction data with auction_date, security_type, offering_amt, etc.
    operations : pd.DataFrame
        Operation panel with operation_date.
    window_days : int
        Days before/after each operation to search for auctions.

    Returns
    -------
    pd.DataFrame
        One row per operation date with replacement issuance summary.
    """
    ops = operations.copy()
    ops["operation_date"] = pd.to_datetime(ops["operation_date"])
    auct = auctions.copy()
    auct["auction_date"] = pd.to_datetime(auct["auction_date"])
    auct["offering_amt"] = pd.to_numeric(auct["offering_amt"], errors="coerce")

    # Compute maturity_years for auctions
    if "maturity_date" in auct.columns:
        auct["maturity_date"] = pd.to_datetime(auct["maturity_date"], errors="coerce")
        auct["auction_maturity_years"] = (
            auct["maturity_date"] - auct["auction_date"]
        ).dt.days / 365.25

    op_dates = ops[["operation_date"]].drop_duplicates().sort_values("operation_date")

    results = []
    for _, row in op_dates.iterrows():
        op_date = row["operation_date"]
        start = op_date - pd.Timedelta(days=window_days)
        end = op_date + pd.Timedelta(days=window_days)

        nearby = auct[(auct["auction_date"] >= start) & (auct["auction_date"] <= end)]

        entry = {
            "operation_date": op_date,
            "n_nearby_auctions": len(nearby),
            "total_issuance": nearby["offering_amt"].sum(),
        }

        # Break down by security type
        for sec_type in ["Bill", "Note", "Bond", "TIPS", "FRN"]:
            mask = nearby["security_type"] == sec_type
            entry[f"issuance_{sec_type.lower()}"] = nearby.loc[mask, "offering_amt"].sum()

        # Also check the asset_class column (used by TreasuryDirect data)
        if "asset_class" in nearby.columns:
            for ac in ["TIPS", "FRN"]:
                ac_mask = nearby["asset_class"] == ac
                key = f"issuance_{ac.lower()}"
                entry[key] = entry.get(key, 0) + nearby.loc[ac_mask, "offering_amt"].sum()

        # Average maturity of nearby issuance (if available)
        if "auction_maturity_years" in nearby.columns:
            weighted = nearby.dropna(subset=["auction_maturity_years", "offering_amt"])
            if not weighted.empty and weighted["offering_amt"].sum() > 0:
                entry["avg_nearby_maturity_years"] = (
                    weighted["auction_maturity_years"] * weighted["offering_amt"]
                ).sum() / weighted["offering_amt"].sum()

        results.append(entry)

    nearby_df = pd.DataFrame(results)
    logger.info("Computed nearby gross issuance for %d operation dates", len(nearby_df))
    return nearby_df


def build_duration_redistribution_table(
    operations: pd.DataFrame,
    auctions: pd.DataFrame,
    *,
    window_days: int = 14,
) -> pd.DataFrame:
    """Build the comprehensive duration redistribution summary.

    Compares what was retired (buybacks) with what was issued (auctions)
    in the same time window.

    Returns
    -------
    pd.DataFrame
        Summary table with retired and replacement columns per operation date.
    """
    ops = operations.copy()
    ops["operation_date"] = pd.to_datetime(ops["operation_date"])

    amount_col = (
        "par_amount_accepted" if "par_amount_accepted" in ops.columns else "accepted_amount"
    )

    # Aggregate buyback retirements by date
    retired = (
        ops.groupby("operation_date")
        .agg(
            n_securities_retired=("cusip", "count"),
            par_retired=(amount_col, "sum"),
            duration_retired=("duration_dollars", "sum"),
            avg_retired_maturity=("maturity_years", "mean"),
            avg_retired_duration=("modified_duration", "mean"),
        )
        .reset_index()
    )

    # Get nearby gross issuance (context, not matched replacement)
    nearby = compute_nearby_gross_issuance(auctions, operations, window_days=window_days)

    # Merge
    table = retired.merge(nearby, on="operation_date", how="left")
    table = table.sort_values("operation_date").reset_index(drop=True)

    # Compute ratios (labeled as gross, not matched)
    table["gross_issuance_to_retirement_ratio"] = table["total_issuance"] / table["par_retired"]

    if "avg_nearby_maturity_years" in table.columns:
        table["nearby_maturity_shift"] = (
            table["avg_nearby_maturity_years"] - table["avg_retired_maturity"]
        )

    logger.info(
        "Duration redistribution table: %d operations, "
        "total retired $%.1fB, nearby gross issuance $%.1fB",
        len(table),
        table["par_retired"].sum() / 1e9,
        table["total_issuance"].sum() / 1e9,
    )
    return table


def build_bucketed_redistribution_summary(
    operations: pd.DataFrame,
) -> pd.DataFrame:
    """Produce the canonical bucketed duration summary.

    This is the "one durable duration summary table" required by Milestone 5.
    """
    amount_col = (
        "par_amount_accepted" if "par_amount_accepted" in operations.columns else "accepted_amount"
    )

    summary = (
        operations.groupby("maturity_bucket")
        .agg(
            n_operations=("operation_date", "nunique"),
            n_securities=("cusip", "count"),
            par_retired=(amount_col, "sum"),
            avg_coupon_rate=("coupon_rate", "mean"),
            avg_yield_proxy=("yield_proxy", "mean"),
            avg_maturity_years=("maturity_years", "mean"),
            avg_modified_duration=("modified_duration", "mean"),
            avg_dv01=("dv01", "mean"),
            total_duration_dollars=("duration_dollars", "sum"),
            total_dv01=("dv01", "sum"),
        )
        .reset_index()
    )

    # Add percentage columns
    total_par = summary["par_retired"].sum()
    total_dur = summary["total_duration_dollars"].sum()
    summary["pct_par"] = (summary["par_retired"] / total_par * 100).round(1)
    summary["pct_duration"] = (summary["total_duration_dollars"] / total_dur * 100).round(1)

    logger.info("Bucketed redistribution summary: %d buckets", len(summary))
    return summary

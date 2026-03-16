"""Event-window analytics for buyback operations.

Computes pre/post changes in dealer positions and yields around
operation dates using exact offset targeting (not nearest-observation).
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def _pick_at_offset(
    series_index: pd.DatetimeIndex, anchor: pd.Timestamp, offset_days: int, direction: str
) -> pd.Timestamp | None:
    """Find the observation closest to exactly `offset_days` from anchor.

    For weekly dealer data (direction='backward'): find the observation
    whose date is closest to `anchor - offset_days` within that series.
    For daily yield data: same logic.

    Returns None if no observation is within 5 days of the target.
    """
    target = anchor + pd.Timedelta(days=offset_days)
    if series_index.empty:
        return None
    idx = series_index.get_indexer([target], method="nearest")[0]
    nearest = series_index[idx]
    if abs((nearest - target).days) > 5:
        return None
    return nearest


def compute_dealer_event_windows(
    operations: pd.DataFrame,
    dealer_positions: pd.DataFrame,
    *,
    pre_weeks: int = 2,
    post_weeks: int = 2,
) -> pd.DataFrame:
    """Compute pre/post dealer position changes around each operation.

    Selects the observation closest to exactly `pre_weeks` before and
    `post_weeks` after the operation date, rather than simply taking the
    nearest-before and nearest-after observations.

    Parameters
    ----------
    operations : pd.DataFrame
        Operation panel with 'operation_date' column.
    dealer_positions : pd.DataFrame
        Weekly dealer positions indexed by date.
    pre_weeks, post_weeks : int
        Exact number of weeks before/after to target.

    Returns
    -------
    pd.DataFrame
        One row per operation with pre/post dealer position columns and
        the actual dates used (dealer_pre_date, dealer_post_date).
    """
    ops = operations.copy()
    ops["operation_date"] = pd.to_datetime(ops["operation_date"])
    op_dates = ops[["operation_date"]].drop_duplicates().sort_values("operation_date")

    results = []
    for _, row in op_dates.iterrows():
        op_date = row["operation_date"]
        entry = {"operation_date": op_date}

        pre_date = _pick_at_offset(dealer_positions.index, op_date, -pre_weeks * 7, "backward")
        post_date = _pick_at_offset(dealer_positions.index, op_date, post_weeks * 7, "forward")

        entry["dealer_pre_date"] = pre_date
        entry["dealer_post_date"] = post_date
        entry["dealer_window_complete"] = pre_date is not None and post_date is not None

        if pre_date is not None and post_date is not None:
            pre_val = dealer_positions.loc[pre_date]
            post_val = dealer_positions.loc[post_date]
            for col in dealer_positions.columns:
                entry[f"dealer_pre_{col}"] = pre_val.get(col)
                entry[f"dealer_post_{col}"] = post_val.get(col)
                pre_v = pre_val.get(col)
                post_v = post_val.get(col)
                if pd.notna(pre_v) and pd.notna(post_v):
                    entry[f"dealer_change_{col}"] = post_v - pre_v

        results.append(entry)

    event_df = pd.DataFrame(results)
    logger.info("Computed dealer event windows for %d operation dates", len(event_df))
    return event_df


def compute_yield_event_windows(
    operations: pd.DataFrame,
    h15_rates: pd.DataFrame,
    *,
    pre_days: int = 5,
    post_days: int = 5,
) -> pd.DataFrame:
    """Compute pre/post yield changes around each operation.

    Selects the observation closest to exactly `pre_days` before and
    `post_days` after the operation date.

    Parameters
    ----------
    operations : pd.DataFrame
        Operation panel with 'operation_date' column.
    h15_rates : pd.DataFrame
        Daily H.15 rates indexed by date.
    pre_days, post_days : int
        Exact number of calendar days before/after to target.

    Returns
    -------
    pd.DataFrame
        One row per operation with pre/post yield columns and
        the actual dates used (yield_pre_date, yield_post_date).
    """
    ops = operations.copy()
    ops["operation_date"] = pd.to_datetime(ops["operation_date"])
    op_dates = ops[["operation_date"]].drop_duplicates().sort_values("operation_date")

    results = []
    for _, row in op_dates.iterrows():
        op_date = row["operation_date"]
        entry = {"operation_date": op_date}

        pre_date = _pick_at_offset(h15_rates.index, op_date, -pre_days, "backward")
        post_date = _pick_at_offset(h15_rates.index, op_date, post_days, "forward")

        entry["yield_pre_date"] = pre_date
        entry["yield_post_date"] = post_date
        entry["yield_window_complete"] = pre_date is not None and post_date is not None

        if pre_date is not None and post_date is not None:
            pre_val = h15_rates.loc[pre_date]
            post_val = h15_rates.loc[post_date]
            for col in h15_rates.columns:
                entry[f"yield_pre_{col}"] = pre_val.get(col)
                entry[f"yield_post_{col}"] = post_val.get(col)
                pre_v = pre_val.get(col)
                post_v = post_val.get(col)
                if pd.notna(pre_v) and pd.notna(post_v):
                    entry[f"yield_change_{col}"] = post_v - pre_v

        results.append(entry)

    event_df = pd.DataFrame(results)
    logger.info("Computed yield event windows for %d operation dates", len(event_df))
    return event_df


def build_event_study_panel(
    operations: pd.DataFrame,
    dealer_positions: pd.DataFrame,
    h15_rates: pd.DataFrame,
) -> pd.DataFrame:
    """Build a merged event-study panel with operation + dealer + yield data.

    Returns one row per unique operation date with:
    - Operation summary (total par accepted, operation type, etc.)
    - Pre/post dealer position changes (at exact offset)
    - Pre/post yield changes (at exact offset)
    """
    ops = operations.copy()
    ops["operation_date"] = pd.to_datetime(ops["operation_date"])

    op_summary = (
        ops.groupby("operation_date")
        .agg(
            n_securities=("cusip", "count"),
            total_par_accepted=("par_amount_accepted", "sum"),
            total_duration_dollars=("duration_dollars", "sum"),
            avg_maturity_years=("maturity_years", "mean"),
            operation_types=("operation_type", lambda x: "|".join(sorted(x.unique()))),
            security_types=("security_type", lambda x: "|".join(sorted(x.unique()))),
        )
        .reset_index()
    )

    dealer_events = compute_dealer_event_windows(ops, dealer_positions)
    yield_events = compute_yield_event_windows(ops, h15_rates)

    panel = op_summary.merge(dealer_events, on="operation_date", how="left")
    panel = panel.merge(yield_events, on="operation_date", how="left")
    panel = panel.sort_values("operation_date").reset_index(drop=True)

    logger.info(
        "Built event-study panel: %d operations, %d columns",
        len(panel),
        len(panel.columns),
    )
    return panel

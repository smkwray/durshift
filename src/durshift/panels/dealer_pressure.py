from __future__ import annotations

import pandas as pd


def attach_nearest_dealer_snapshot(
    operation_panel: pd.DataFrame,
    dealer_frame: pd.DataFrame,
    *,
    dealer_date_column: str = "week_ending",
) -> pd.DataFrame:
    """Attach the nearest prior dealer-data observation to each operation."""

    left = operation_panel.sort_values("operation_date").copy()
    right = dealer_frame.sort_values(dealer_date_column).copy()

    left["operation_date"] = pd.to_datetime(left["operation_date"])
    right[dealer_date_column] = pd.to_datetime(right[dealer_date_column])

    return pd.merge_asof(
        left,
        right,
        left_on="operation_date",
        right_on=dealer_date_column,
        direction="backward",
    )

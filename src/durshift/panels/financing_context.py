from __future__ import annotations

import pandas as pd


def attach_financing_context(
    operation_panel: pd.DataFrame,
    issuance_frame: pd.DataFrame,
    *,
    issuance_date_column: str = "auction_date",
) -> pd.DataFrame:
    """Attach the nearest prior issuance snapshot to each operation.

    This is a coarse seed implementation meant to stabilize the intended merge pattern.
    """

    left = operation_panel.sort_values("operation_date").copy()
    right = issuance_frame.sort_values(issuance_date_column).copy()

    left["operation_date"] = pd.to_datetime(left["operation_date"])
    right[issuance_date_column] = pd.to_datetime(right[issuance_date_column])

    return pd.merge_asof(
        left,
        right,
        left_on="operation_date",
        right_on=issuance_date_column,
        direction="backward",
    )

import pandas as pd

from durshift.data.contracts import OPERATION_PANEL_COLUMNS
from durshift.panels.operations import normalize_operation_panel


def test_normalize_operation_panel_builds_expected_columns() -> None:
    frame = pd.DataFrame(
        [
            {
                "announcement_date": "2025-02-03",
                "operation_date": "2025-02-05",
                "security_type": "NominalCoupon",
                "maturity_years": 14.8,
                "coupon_rate": 0.0425,
                "yield_proxy": 0.0440,
                "accepted_amount": 1_800_000_000,
                "offered_amount": 2_000_000_000,
                "issue_date": "2014-05-15",
                "stated_purpose": "liquidity_support",
                "buyback_bucket": "10Y-20Y",
                "notes": "test row",
                "replacement_maturity_years": 10.0,
            }
        ]
    )

    panel = normalize_operation_panel(frame)

    assert list(panel.columns) == OPERATION_PANEL_COLUMNS
    assert panel.loc[0, "accepted_share"] == 0.9
    assert panel.loc[0, "purpose_label"] == "liquidity_support"
    assert panel.loc[0, "maturity_bucket"] == "10-20Y"
    assert panel.loc[0, "dv01"] > 0

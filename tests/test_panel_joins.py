from __future__ import annotations

import pandas as pd

from durshift.panels.dealer_pressure import attach_nearest_dealer_snapshot
from durshift.panels.financing_context import attach_financing_context


def test_attach_financing_context_merges_backward():
    ops = pd.DataFrame(
        {
            "operation_date": pd.to_datetime(["2025-03-15", "2025-06-15"]),
            "accepted_amount": [1_000_000, 2_000_000],
        }
    )
    issuance = pd.DataFrame(
        {
            "auction_date": pd.to_datetime(["2025-01-10", "2025-05-01"]),
            "auction_size": [50_000, 60_000],
        }
    )
    result = attach_financing_context(ops, issuance)
    assert "auction_size" in result.columns
    assert len(result) == 2
    # Mar 15 should pick up Jan 10 issuance (backward)
    row_mar = result[result["accepted_amount"] == 1_000_000].iloc[0]
    assert row_mar["auction_size"] == 50_000
    # Jun 15 should pick up May 1 issuance (backward, nearest)
    row_jun = result[result["accepted_amount"] == 2_000_000].iloc[0]
    assert row_jun["auction_size"] == 60_000


def test_attach_nearest_dealer_snapshot_merges_backward():
    ops = pd.DataFrame(
        {
            "operation_date": pd.to_datetime(["2025-04-10"]),
            "accepted_amount": [1_000_000],
        }
    )
    dealer = pd.DataFrame(
        {
            "week_ending": pd.to_datetime(["2025-04-04", "2025-04-11"]),
            "net_position": [100, 200],
        }
    )
    result = attach_nearest_dealer_snapshot(ops, dealer)
    assert "net_position" in result.columns
    # Apr 10 should pick up Apr 4 (backward, before Apr 11)
    assert result.iloc[0]["net_position"] == 100

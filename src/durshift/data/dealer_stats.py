from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DealerStatsSource:
    homepage: str
    note: str


PRIMARY_DEALER_STATS = DealerStatsSource(
    homepage="https://www.newyorkfed.org/markets/counterparties/primary-dealers-statistics",
    note=(
        "Weekly series include positions, transactions, financing, and fails;"
        " publication lag matters."
    ),
)

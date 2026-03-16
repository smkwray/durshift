from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DebtOutstandingSource:
    homepage: str
    note: str


MONTHLY_PUBLIC_DEBT = DebtOutstandingSource(
    homepage="https://fiscaldata.treasury.gov/datasets/monthly-statement-public-debt/",
    note="Use for maturity composition and average length context.",
)

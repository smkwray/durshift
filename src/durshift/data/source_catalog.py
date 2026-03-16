from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceSpec:
    name: str
    owner: str
    homepage: str
    note: str


SOURCE_CATALOG = [
    SourceSpec(
        name="treasury_buybacks",
        owner="U.S. Treasury / TreasuryDirect",
        homepage="https://www.treasurydirect.gov/auctions/results/",
        note="Buyback announcements and results are linked from TreasuryDirect auction pages.",
    ),
    SourceSpec(
        name="treasury_auctions",
        owner="U.S. Treasury Fiscal Data",
        homepage="https://fiscaldata.treasury.gov/datasets/treasury-securities-auctions-data/",
        note="Prefer machine-readable auction series when possible.",
    ),
    SourceSpec(
        name="primary_dealer_statistics",
        owner="Federal Reserve Bank of New York",
        homepage="https://www.newyorkfed.org/markets/counterparties/primary-dealers-statistics",
        note="Weekly aggregates for positions, transactions, financing, and fails.",
    ),
    SourceSpec(
        name="h15_rates",
        owner="Federal Reserve Board",
        homepage="https://www.federalreserve.gov/releases/h15/",
        note="Daily context rates and Treasury yield proxies.",
    ),
    SourceSpec(
        name="debt_outstanding",
        owner="U.S. Treasury Fiscal Data",
        homepage="https://fiscaldata.treasury.gov/datasets/monthly-statement-public-debt/",
        note="Use for maturity composition and debt outstanding context.",
    ),
]

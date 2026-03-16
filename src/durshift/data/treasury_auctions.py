from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuctionSourceNote:
    name: str
    homepage: str
    machine_readable_preference: bool
    note: str


AUCTION_SOURCES = [
    AuctionSourceNote(
        name="Fiscal Data Treasury Securities Auctions Data",
        homepage="https://fiscaldata.treasury.gov/datasets/treasury-securities-auctions-data/",
        machine_readable_preference=True,
        note="Preferred historical source for announcements and auctioned amounts.",
    ),
    AuctionSourceNote(
        name="TreasuryDirect announcements and results",
        homepage="https://www.treasurydirect.gov/auctions/announcements-data-results/",
        machine_readable_preference=False,
        note="Useful for current-page cross-checking and announcement context.",
    ),
]

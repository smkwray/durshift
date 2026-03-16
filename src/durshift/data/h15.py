from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class H15Source:
    homepage: str
    note: str


H15_DAILY = H15Source(
    homepage="https://www.federalreserve.gov/releases/h15/",
    note="Daily selected interest rates; useful as a simple yield-context source.",
)

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SomaSource:
    homepage: str
    note: str


SOMA_HOLDINGS = SomaSource(
    homepage="https://www.newyorkfed.org/markets/soma-holdings",
    note="Optional control for changes in public duration supply driven by the Fed.",
)

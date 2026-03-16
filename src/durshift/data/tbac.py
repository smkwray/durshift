from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InstitutionalDocument:
    name: str
    homepage: str
    note: str


INSTITUTIONAL_DOCUMENTS = [
    InstitutionalDocument(
        name="Treasury press releases index",
        homepage="https://home.treasury.gov/news/press-releases",
        note="Use quarterly refunding statements for schedule and purpose changes.",
    ),
]

from __future__ import annotations

from datetime import date, datetime


def parse_date(value: str | date | datetime) -> date:
    """Parse common date-like inputs into a ``date``."""

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)).date()

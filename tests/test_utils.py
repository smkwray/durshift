from __future__ import annotations

from datetime import date, datetime

from durshift.utils.dates import parse_date
from durshift.utils.files import ensure_parent_dir


def test_parse_date_from_string():
    assert parse_date("2025-06-15") == date(2025, 6, 15)


def test_parse_date_from_datetime():
    assert parse_date(datetime(2025, 6, 15, 10, 30)) == date(2025, 6, 15)


def test_parse_date_from_date():
    d = date(2025, 6, 15)
    assert parse_date(d) is d


def test_ensure_parent_dir_creates_parents(tmp_path):
    nested = tmp_path / "a" / "b" / "out.csv"
    result = ensure_parent_dir(nested)
    assert result == nested
    assert nested.parent.is_dir()

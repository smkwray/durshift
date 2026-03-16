"""Tests for durshift.data.ny_fed_dealers.

Uses monkeypatched requests.get to avoid real HTTP calls.
"""

from __future__ import annotations

import pandas as pd

from durshift.data.ny_fed_dealers import fetch_dealer_positions, fetch_dealer_series


class _FakeResponse:
    status_code = 200

    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        pass


_SAMPLE_CSV = (
    "date,series_id,value\n"
    "2025-03-05,PDPOSGST-TOT,100000\n"
    "2025-03-12,PDPOSGST-TOT,105000\n"
    "2025-03-19,PDPOSGST-TOT,102000\n"
)


# ── fetch_dealer_series ─────────────────────────────────────────────


def test_fetch_dealer_series_returns_dataframe(monkeypatch):
    def fake_get(url, timeout=None):
        return _FakeResponse(_SAMPLE_CSV)

    monkeypatch.setattr("durshift.data.ny_fed_dealers.requests.get", fake_get)

    result = fetch_dealer_series("PDPOSGST-TOT")
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 3
    assert list(result.columns) == ["date", "series_id", "value_millions"]


def test_fetch_dealer_series_parses_dates(monkeypatch):
    def fake_get(url, timeout=None):
        return _FakeResponse(_SAMPLE_CSV)

    monkeypatch.setattr("durshift.data.ny_fed_dealers.requests.get", fake_get)

    result = fetch_dealer_series("PDPOSGST-TOT")
    assert pd.api.types.is_datetime64_any_dtype(result["date"])


def test_fetch_dealer_series_coerces_values(monkeypatch):
    csv_with_bad = "date,series_id,value\n2025-03-05,X,100\n2025-03-12,X,ND\n"

    def fake_get(url, timeout=None):
        return _FakeResponse(csv_with_bad)

    monkeypatch.setattr("durshift.data.ny_fed_dealers.requests.get", fake_get)

    result = fetch_dealer_series("X")
    assert pd.isna(result["value_millions"].iloc[1])


# ── fetch_dealer_positions ──────────────────────────────────────────


def test_fetch_dealer_positions_wide_format(monkeypatch):
    csv_a = "date,series_id,value\n2025-03-05,A,10\n2025-03-12,A,20\n"
    csv_b = "date,series_id,value\n2025-03-05,B,30\n2025-03-12,B,40\n"

    call_count = 0

    def fake_get(url, timeout=None):
        nonlocal call_count
        call_count += 1
        if "SERIES_A" in url:
            return _FakeResponse(csv_a)
        return _FakeResponse(csv_b)

    monkeypatch.setattr("durshift.data.ny_fed_dealers.requests.get", fake_get)

    series_map = {"SERIES_A": "col_a", "SERIES_B": "col_b"}
    result = fetch_dealer_positions(series_map=series_map)

    assert isinstance(result, pd.DataFrame)
    assert "col_a" in result.columns
    assert "col_b" in result.columns
    assert len(result) == 2
    assert result.index.name == "date"


def test_fetch_dealer_positions_handles_partial_failure(monkeypatch):
    csv_ok = "date,series_id,value\n2025-03-05,OK,50\n"

    def fake_get(url, timeout=None):
        if "BAD" in url:
            raise ConnectionError("simulated failure")
        return _FakeResponse(csv_ok)

    monkeypatch.setattr("durshift.data.ny_fed_dealers.requests.get", fake_get)

    series_map = {"OK_SERIES": "good", "BAD_SERIES": "bad"}
    result = fetch_dealer_positions(series_map=series_map)

    assert isinstance(result, pd.DataFrame)
    assert "good" in result.columns
    # The bad series is silently skipped
    assert "bad" not in result.columns


def test_fetch_dealer_positions_all_fail(monkeypatch):
    def fake_get(url, timeout=None):
        raise ConnectionError("simulated")

    monkeypatch.setattr("durshift.data.ny_fed_dealers.requests.get", fake_get)

    result = fetch_dealer_positions(series_map={"X": "x"})
    assert isinstance(result, pd.DataFrame)
    assert result.empty

"""Tests for the Fiscal Data API client.

Uses monkeypatched responses to avoid real HTTP calls.
"""

from __future__ import annotations

import pandas as pd

from durshift.data.fiscal_data_api import fetch_auctions


class _FakeResponse:
    status_code = 200

    def __init__(self, data, total_pages=1):
        self._payload = {
            "data": data,
            "meta": {"count": len(data), "total-count": len(data), "total-pages": total_pages},
        }

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_fetch_auctions_returns_dataframe(monkeypatch):
    sample_records = [
        {
            "cusip": "912797AA1",
            "security_type": "Bill",
            "auction_date": "2025-01-02",
            "offering_amt": "50000000000",
        },
        {
            "cusip": "91282CCC3",
            "security_type": "Note",
            "auction_date": "2025-01-08",
            "offering_amt": "25000000000",
        },
    ]

    def fake_get(url, params=None, timeout=None):
        return _FakeResponse(sample_records)

    monkeypatch.setattr("durshift.data.fiscal_data_api.requests.get", fake_get)

    result = fetch_auctions(min_auction_date="2025-01-01")
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert "cusip" in result.columns
    assert "security_type" in result.columns


def test_fetch_auctions_empty_result(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return _FakeResponse([])

    monkeypatch.setattr("durshift.data.fiscal_data_api.requests.get", fake_get)

    result = fetch_auctions(min_auction_date="2099-01-01")
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0


def test_fetch_auctions_paginates(monkeypatch):
    page1_data = [{"cusip": "AAA", "security_type": "Bill", "auction_date": "2025-01-02"}]
    page2_data = [{"cusip": "BBB", "security_type": "Note", "auction_date": "2025-01-03"}]

    call_count = 0

    def fake_get(url, params=None, timeout=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _FakeResponse(page1_data, total_pages=2)
        return _FakeResponse(page2_data, total_pages=2)

    monkeypatch.setattr("durshift.data.fiscal_data_api.requests.get", fake_get)

    result = fetch_auctions()
    assert len(result) == 2
    assert call_count == 2

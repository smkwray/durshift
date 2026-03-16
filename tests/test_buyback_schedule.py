"""Tests for buyback schedule XML parsing.

Uses a minimal synthetic XML fixture to avoid network calls.
"""

from __future__ import annotations

import textwrap

import pandas as pd

from durshift.data.buyback_schedule import parse_schedule_xml


def _write_fixture(tmp_path):
    xml_content = textwrap.dedent("""\
        <BuyBackCalendar>
          <BuybackCalendarName>Test Calendar V1</BuybackCalendarName>
          <StartDate>2026-01-15</StartDate>
          <EndDate>2026-04-15</EndDate>
          <BuybackCalendarDate>
            <PurchaseBucketName>Nominal Coupons 5Y to 7Y</PurchaseBucketName>
            <SecurityType>NOMINAL COUPONS</SecurityType>
            <OperationType>Liquidity Support</OperationType>
            <MinimumPurchaseAmountDollars>0</MinimumPurchaseAmountDollars>
            <MaximumPurchaseAmountDollars>4000000000</MaximumPurchaseAmountDollars>
            <MaturityDateRangeStart>2031-01-16</MaturityDateRangeStart>
            <MaturityDateRangeEnd>2033-01-15</MaturityDateRangeEnd>
            <AnnouncementDate>2026-01-14</AnnouncementDate>
            <OperationDate>2026-01-15</OperationDate>
            <SettlementDate>2026-01-16</SettlementDate>
            <OperationStartTimeEasternUS>13:40</OperationStartTimeEasternUS>
            <OperationEndTimeEasternUS>14:00</OperationEndTimeEasternUS>
          </BuybackCalendarDate>
          <BuybackCalendarDate>
            <PurchaseBucketName>TIPS 1Y to 10Y</PurchaseBucketName>
            <SecurityType>TIPS</SecurityType>
            <OperationType>Liquidity Support</OperationType>
            <MinimumPurchaseAmountDollars>0</MinimumPurchaseAmountDollars>
            <MaximumPurchaseAmountDollars>750000000</MaximumPurchaseAmountDollars>
            <MaturityDateRangeStart>2027-01-20</MaturityDateRangeStart>
            <MaturityDateRangeEnd>2036-01-19</MaturityDateRangeEnd>
            <AnnouncementDate>2026-01-19</AnnouncementDate>
            <OperationDate>2026-01-20</OperationDate>
            <SettlementDate>2026-01-21</SettlementDate>
            <OperationStartTimeEasternUS>13:40</OperationStartTimeEasternUS>
            <OperationEndTimeEasternUS>14:00</OperationEndTimeEasternUS>
          </BuybackCalendarDate>
        </BuyBackCalendar>
    """)
    fixture = tmp_path / "test_schedule.xml"
    fixture.write_text(xml_content, encoding="utf-8")
    return fixture


def test_parse_schedule_returns_metadata_and_frame(tmp_path):
    fixture = _write_fixture(tmp_path)
    metadata, frame = parse_schedule_xml(fixture)
    assert metadata["calendar_name"] == "Test Calendar V1"
    assert metadata["start_date"] == "2026-01-15"
    assert metadata["end_date"] == "2026-04-15"
    assert len(frame) == 2


def test_parse_schedule_columns(tmp_path):
    fixture = _write_fixture(tmp_path)
    _metadata, frame = parse_schedule_xml(fixture)
    assert "purchase_bucket" in frame.columns
    assert "security_type" in frame.columns
    assert "operation_type" in frame.columns
    assert "max_purchase_amount" in frame.columns
    assert "operation_date" in frame.columns


def test_parse_schedule_numeric_conversion(tmp_path):
    fixture = _write_fixture(tmp_path)
    _metadata, frame = parse_schedule_xml(fixture)
    assert frame.iloc[0]["max_purchase_amount"] == 4_000_000_000
    assert frame.iloc[1]["max_purchase_amount"] == 750_000_000


def test_parse_schedule_date_conversion(tmp_path):
    fixture = _write_fixture(tmp_path)
    _metadata, frame = parse_schedule_xml(fixture)
    assert pd.api.types.is_datetime64_any_dtype(frame["operation_date"])
    assert frame.iloc[0]["operation_date"] == pd.Timestamp("2026-01-15")

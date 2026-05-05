"""Tests for :mod:`src.finance.sheets` — Google Sheets writer.

Mocks gspread/google-auth at the import surface; no network calls.
"""
from __future__ import annotations

import base64
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


SAMPLE_ARTIFACT = {
    "schema_version": 1,
    "generated_at": "2026-05-04T13:55:00-04:00",
    "cycle": "2026",
    "candidates": [
        {
            "id": "bauer-heather-75",
            "name": "Heather Bauer",
            "district": 75,
            "party": "D",
            "filing_status": "filed",
            "latest_report": {
                "reportId": "418208",
                "report_type": "Quarterly",
                "period_label": "Q1 2026",
                "filed_date": "2026-04-10",
                "url": "https://ethicsfiling.sc.gov/r/418208",
                "is_amended": False,
                "period_raised": 32806.90,
                "total_raised": 89372.11,
                "cash_on_hand": 68448.57,
            },
            "history": [],
            "last_error": None,
        },
        {
            "id": "smith-alice-12",
            "name": "Alice Smith",
            "district": 12,
            "party": "D",
            "filing_status": "filed",
            "latest_report": {
                "reportId": "418000",
                "report_type": "Quarterly",
                "period_label": "Q1 2026",
                "filed_date": "2026-04-09",
                "url": "https://ethicsfiling.sc.gov/r/418000",
                "is_amended": False,
                "period_raised": 1000.0,
                "total_raised": 5000.0,
                "cash_on_hand": 2000.0,
            },
            "history": [],
            "last_error": None,
        },
        {
            "id": "doe-john-99",
            "name": "John Doe",
            "district": 99,
            "party": "D",
            "filing_status": "not_filed",
            "latest_report": None,
            "history": [],
            "last_error": None,
        },
    ],
    "stats": {},
}

SHEET_ID = "test_sheet_id_123"


def _install_fake_gspread(monkeypatch, worksheet_mock=None, raise_on=None):
    """Install fake gspread + google.oauth2 modules and return the worksheet mock.

    ``raise_on`` (str or None): if set, the named operation raises RuntimeError.
        One of: 'authorize', 'open', 'worksheet', 'update'.
    """
    if worksheet_mock is None:
        worksheet_mock = MagicMock()

    if raise_on == "update":
        worksheet_mock.update.side_effect = RuntimeError("transport boom")

    spreadsheet = MagicMock()
    if raise_on == "worksheet":
        spreadsheet.worksheet.side_effect = RuntimeError("not found")
        spreadsheet.add_worksheet.side_effect = RuntimeError("create boom")
    else:
        spreadsheet.worksheet.return_value = worksheet_mock

    client = MagicMock()
    if raise_on == "open":
        client.open_by_key.side_effect = RuntimeError("open boom")
    else:
        client.open_by_key.return_value = spreadsheet

    fake_gspread = SimpleNamespace(authorize=MagicMock(return_value=client))
    if raise_on == "authorize":
        fake_gspread.authorize.side_effect = RuntimeError("auth boom")

    fake_creds_cls = MagicMock()
    fake_creds_cls.from_service_account_info.return_value = SimpleNamespace()

    fake_service_account_module = SimpleNamespace(Credentials=fake_creds_cls)
    fake_oauth2 = SimpleNamespace(service_account=fake_service_account_module)
    fake_google = SimpleNamespace(oauth2=fake_oauth2)

    import sys

    monkeypatch.setitem(sys.modules, "gspread", fake_gspread)
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.oauth2", fake_oauth2)
    monkeypatch.setitem(
        sys.modules, "google.oauth2.service_account", fake_service_account_module
    )
    return worksheet_mock


def test_skips_when_credentials_missing(monkeypatch, caplog):
    monkeypatch.delenv("GOOGLE_SHEETS_CREDENTIALS", raising=False)
    from src.finance.sheets import sync_house_finance_to_sheet

    with caplog.at_level("WARNING"):
        result = sync_house_finance_to_sheet(SAMPLE_ARTIFACT, SHEET_ID)
    assert result is False
    assert any("GOOGLE_SHEETS_CREDENTIALS" in m for m in caplog.messages)


def test_skips_when_sheet_id_empty(monkeypatch, caplog):
    monkeypatch.setenv("GOOGLE_SHEETS_CREDENTIALS", json.dumps({"x": 1}))
    from src.finance.sheets import sync_house_finance_to_sheet

    with caplog.at_level("WARNING"):
        result = sync_house_finance_to_sheet(SAMPLE_ARTIFACT, "")
    assert result is False
    assert any("sheet_id is empty" in m for m in caplog.messages)


def test_writes_header_and_rows_in_correct_order(monkeypatch):
    monkeypatch.setenv(
        "GOOGLE_SHEETS_CREDENTIALS", json.dumps({"type": "service_account"})
    )
    ws = _install_fake_gspread(monkeypatch)
    from src.finance.sheets import HEADERS, sync_house_finance_to_sheet

    result = sync_house_finance_to_sheet(SAMPLE_ARTIFACT, SHEET_ID)
    assert result is True

    ws.clear.assert_called_once()
    ws.update.assert_called_once()
    args, kwargs = ws.update.call_args
    cell, rows = args[0], args[1]
    assert cell == "A1"
    # Row 0 is header, rows 1-3 are candidates.
    assert rows[0] == HEADERS
    assert len(rows) == 1 + 3  # header + 3 candidates
    # Filed candidates sorted by COH desc: Bauer (68448.57) before Smith (2000.0).
    assert rows[1][0] == "Heather Bauer"
    assert rows[2][0] == "Alice Smith"
    # Not-filed sorts last.
    assert rows[3][0] == "John Doe"


def test_heather_bauer_row_exact_format(monkeypatch):
    """The exact row format for Heather Bauer required by the spec."""
    monkeypatch.setenv(
        "GOOGLE_SHEETS_CREDENTIALS", json.dumps({"type": "service_account"})
    )
    ws = _install_fake_gspread(monkeypatch)
    from src.finance.sheets import sync_house_finance_to_sheet

    sync_house_finance_to_sheet(SAMPLE_ARTIFACT, SHEET_ID)
    rows = ws.update.call_args[0][1]
    bauer_row = rows[1]

    assert bauer_row == [
        "Heather Bauer",
        75,
        "D",
        "filed",
        "$32,806.90",
        "$89,372.11",
        "$68,448.57",
        "2026-04-10",
        "Quarterly",
        "Q1 2026",
        "https://ethicsfiling.sc.gov/r/418208",
        "2026-05-04T13:55:00-04:00",
    ]


def test_not_filed_candidate_has_blank_money_fields(monkeypatch):
    monkeypatch.setenv(
        "GOOGLE_SHEETS_CREDENTIALS", json.dumps({"type": "service_account"})
    )
    ws = _install_fake_gspread(monkeypatch)
    from src.finance.sheets import sync_house_finance_to_sheet

    sync_house_finance_to_sheet(SAMPLE_ARTIFACT, SHEET_ID)
    rows = ws.update.call_args[0][1]
    doe_row = rows[3]

    assert doe_row[0] == "John Doe"
    assert doe_row[3] == "not_filed"
    # Period raised, total raised, cash on hand all blank
    assert doe_row[4] == ""
    assert doe_row[5] == ""
    assert doe_row[6] == ""
    assert doe_row[7] == ""  # filed date


def test_credentials_via_base64(monkeypatch):
    """Credentials supplied as base64-encoded JSON should work."""
    payload = json.dumps({"type": "service_account", "client_email": "x@y"})
    encoded = base64.b64encode(payload.encode()).decode()
    monkeypatch.setenv("GOOGLE_SHEETS_CREDENTIALS", encoded)
    ws = _install_fake_gspread(monkeypatch)
    from src.finance.sheets import sync_house_finance_to_sheet

    result = sync_house_finance_to_sheet(SAMPLE_ARTIFACT, SHEET_ID)
    assert result is True
    ws.update.assert_called_once()


def test_returns_false_on_authorize_failure(monkeypatch, caplog):
    monkeypatch.setenv(
        "GOOGLE_SHEETS_CREDENTIALS", json.dumps({"type": "service_account"})
    )
    _install_fake_gspread(monkeypatch, raise_on="authorize")
    from src.finance.sheets import sync_house_finance_to_sheet

    with caplog.at_level("WARNING"):
        result = sync_house_finance_to_sheet(SAMPLE_ARTIFACT, SHEET_ID)
    assert result is False
    assert any("connect" in m for m in caplog.messages)


def test_returns_false_on_update_failure(monkeypatch, caplog):
    monkeypatch.setenv(
        "GOOGLE_SHEETS_CREDENTIALS", json.dumps({"type": "service_account"})
    )
    _install_fake_gspread(monkeypatch, raise_on="update")
    from src.finance.sheets import sync_house_finance_to_sheet

    with caplog.at_level("WARNING"):
        result = sync_house_finance_to_sheet(SAMPLE_ARTIFACT, SHEET_ID)
    assert result is False
    assert any("write" in m for m in caplog.messages)


def test_creates_tab_when_missing(monkeypatch):
    """If the worksheet doesn't exist, fall back to add_worksheet."""
    monkeypatch.setenv(
        "GOOGLE_SHEETS_CREDENTIALS", json.dumps({"type": "service_account"})
    )
    new_ws = MagicMock()
    spreadsheet = MagicMock()
    spreadsheet.worksheet.side_effect = RuntimeError("not found")
    spreadsheet.add_worksheet.return_value = new_ws

    client = MagicMock()
    client.open_by_key.return_value = spreadsheet

    fake_gspread = SimpleNamespace(authorize=MagicMock(return_value=client))
    fake_creds_cls = MagicMock()
    fake_creds_cls.from_service_account_info.return_value = SimpleNamespace()
    fake_service_account_module = SimpleNamespace(Credentials=fake_creds_cls)
    fake_oauth2 = SimpleNamespace(service_account=fake_service_account_module)
    fake_google = SimpleNamespace(oauth2=fake_oauth2)

    import sys

    monkeypatch.setitem(sys.modules, "gspread", fake_gspread)
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.oauth2", fake_oauth2)
    monkeypatch.setitem(
        sys.modules, "google.oauth2.service_account", fake_service_account_module
    )

    from src.finance.sheets import HOUSE_FINANCE_TAB, sync_house_finance_to_sheet

    result = sync_house_finance_to_sheet(SAMPLE_ARTIFACT, SHEET_ID)
    assert result is True
    spreadsheet.add_worksheet.assert_called_once()
    kwargs = spreadsheet.add_worksheet.call_args.kwargs
    assert kwargs["title"] == HOUSE_FINANCE_TAB
    new_ws.update.assert_called_once()

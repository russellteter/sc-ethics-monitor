"""Google Sheets sync for the SC House Dem finance scraper.

Writes the contents of ``data/house_finance.json`` to a "House Finance" tab
in the Master Tracker spreadsheet. Designed to be best-effort:

* Fails GRACEFULLY (returns ``False``, logs a warning) when
  ``GOOGLE_SHEETS_CREDENTIALS`` is unset or invalid.
* Imports gspread/google-auth lazily so importing this module doesn't blow
  up on systems without those packages installed.
* Never raises out of :func:`sync_house_finance_to_sheet`; callers can wire
  it after ``build_artifact`` without try/except wrappers (though they
  should still wrap to be safe — see ``src/finance/__main__.py``).

Tab schema (row 1 is the header, candidate rows start at row 2):

    | Candidate | District | Party | Filing Status | Period Raised |
    | Total Raised | Cash on Hand | Filed Date | Report Type |
    | Period Label | Ethics URL | Last Updated |

Numbers are formatted ``$1,234.56``. Dates are ``YYYY-MM-DD``. Rows are
sorted by Cash on Hand descending (filed candidates first, then
not_filed/scrape_failed).
"""
from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Google API scopes (matches src/sheets_sync.py).
_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

# Tab name written by this module.
HOUSE_FINANCE_TAB = "House Finance"

# Header row, in column order. Keep this in sync with ``_row_for_candidate``.
HEADERS = [
    "Candidate",
    "District",
    "Party",
    "Filing Status",
    "Period Raised",
    "Total Raised",
    "Cash on Hand",
    "Filed Date",
    "Report Type",
    "Period Label",
    "Ethics URL",
    "Last Updated",
]


def _load_credentials_dict() -> Optional[dict]:
    """Resolve the GOOGLE_SHEETS_CREDENTIALS env var to a dict.

    Supports the same three forms as ``src/sheets_sync.py``:
        1. Path to a JSON file on disk.
        2. Base64-encoded service-account JSON.
        3. Raw JSON string.

    Returns ``None`` when the env var is unset or unparsable.
    """
    raw = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    if not raw:
        return None

    # 1. File path
    try:
        p = Path(raw)
        if p.exists() and p.is_file():
            with open(p, "r") as f:
                return json.load(f)
    except Exception:
        pass

    # 2. Base64-encoded JSON
    try:
        decoded = base64.b64decode(raw)
        return json.loads(decoded)
    except Exception:
        pass

    # 3. Raw JSON string
    try:
        return json.loads(raw)
    except Exception:
        pass

    return None


def _format_money(value) -> str:
    """Format a numeric value as ``$1,234.56``. Empty string for None/missing."""
    if value is None or value == "":
        return ""
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return ""


def _format_date(value) -> str:
    """Pass through an already-ISO date (``YYYY-MM-DD``); empty for missing."""
    if not value:
        return ""
    return str(value)[:10]


def _row_for_candidate(record: dict, generated_at: str) -> list:
    """Project one candidate dict from the artifact into a sheet row.

    Order matches :data:`HEADERS`. Fields that aren't present (e.g. for
    ``not_filed`` candidates) become empty strings, never ``None``.
    """
    latest = record.get("latest_report") or {}
    return [
        record.get("name", ""),
        record.get("district", ""),
        record.get("party", ""),
        record.get("filing_status", ""),
        _format_money(latest.get("period_raised")),
        _format_money(latest.get("total_raised")),
        _format_money(latest.get("cash_on_hand")),
        _format_date(latest.get("filed_date")),
        latest.get("report_type", "") or "",
        latest.get("period_label", "") or "",
        latest.get("url", "") or "",
        generated_at,
    ]


def _sort_key(record: dict):
    """Sort filed records by Cash on Hand descending; non-filed go last.

    Returns a tuple suitable for ``sorted(..., key=...)``. Records without
    a numeric ``cash_on_hand`` collate after every filed record.
    """
    latest = record.get("latest_report") or {}
    coh = latest.get("cash_on_hand")
    if record.get("filing_status") == "filed" and isinstance(coh, (int, float)):
        # Filed first (0 group), highest COH first (negate for descending).
        return (0, -float(coh))
    return (1, 0)


def _ensure_worksheet(spreadsheet, tab_name: str, header_count: int):
    """Get the named worksheet, creating it with the right column count if missing."""
    try:
        return spreadsheet.worksheet(tab_name)
    except Exception:
        # Most commonly gspread.WorksheetNotFound; create it.
        return spreadsheet.add_worksheet(
            title=tab_name,
            rows=200,
            cols=max(header_count, 12),
        )


def sync_house_finance_to_sheet(artifact: dict, sheet_id: str) -> bool:
    """Write the artifact's candidate rows to the House Finance tab.

    Args:
        artifact: Parsed contents of ``data/house_finance.json``. Must
            contain a ``candidates`` list and a ``generated_at`` string.
        sheet_id: Target spreadsheet ID.

    Returns:
        ``True`` on a successful write. ``False`` (with a warning logged)
        on graceful failure: missing credentials, missing dependency,
        empty sheet_id, or any gspread/transport error.

    This function never raises — callers can invoke it best-effort.
    """
    if not sheet_id:
        logger.warning("sheets sync skipped: sheet_id is empty")
        return False
    if not isinstance(artifact, dict):
        logger.warning("sheets sync skipped: artifact is not a dict")
        return False

    creds_dict = _load_credentials_dict()
    if not creds_dict:
        logger.warning(
            "sheets sync skipped: GOOGLE_SHEETS_CREDENTIALS unset or unparsable"
        )
        return False

    # Lazy imports — keep module importable on systems without gspread.
    try:
        import gspread  # noqa: WPS433 — intentional lazy import
        from google.oauth2.service_account import Credentials  # noqa: WPS433
    except ImportError as e:
        logger.warning("sheets sync skipped: gspread/google-auth not installed (%s)", e)
        return False

    try:
        credentials = Credentials.from_service_account_info(creds_dict, scopes=_SCOPES)
        client = gspread.authorize(credentials)
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = _ensure_worksheet(spreadsheet, HOUSE_FINANCE_TAB, len(HEADERS))
    except Exception as e:  # noqa: BLE001 — graceful degradation
        logger.warning("sheets sync failed during connect: %s", e)
        return False

    candidates = list(artifact.get("candidates") or [])
    candidates.sort(key=_sort_key)
    generated_at = artifact.get("generated_at", "") or ""

    rows = [HEADERS]
    for record in candidates:
        rows.append(_row_for_candidate(record, generated_at))

    try:
        # Wipe existing contents, then write header + data in one call.
        worksheet.clear()
        worksheet.update("A1", rows)
    except Exception as e:  # noqa: BLE001 — graceful degradation
        logger.warning("sheets sync failed during write: %s", e)
        return False

    logger.info(
        "sheets sync wrote %d candidate rows to '%s'",
        len(candidates),
        HOUSE_FINANCE_TAB,
    )
    return True

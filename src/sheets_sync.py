"""
Google Sheets Sync - Integration with Google Sheets "Source of Truth".

Handles adding/updating candidates to the Google Sheet.
Works with the sheet structure initialized by sc-ethics-monitor.
"""

import json
from datetime import datetime
from typing import Optional

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    gspread = None
    Credentials = None

from config import (
    GOOGLE_SHEET_ID,
    get_google_credentials,
    SHEET_TAB_CANDIDATES,
    SHEET_TAB_SYNC_LOG,
    CANDIDATES_HEADERS,
    SYNC_LOG_HEADERS,
)

# Google Sheets API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]


class SheetsSync:
    """
    Google Sheets sync handler.

    Adds new candidates to the existing sheet structure.
    """

    def __init__(self, sheet_id: Optional[str] = None):
        """
        Initialize the sheets sync handler.

        Args:
            sheet_id: Google Sheet ID (from URL). Uses env var if not provided.
        """
        self.sheet_id = sheet_id or GOOGLE_SHEET_ID
        self._client = None
        self._spreadsheet = None
        self._worksheets = {}

    def connect(self) -> bool:
        """
        Connect to Google Sheets.

        Returns:
            True if connection successful, False otherwise.
        """
        if not GSPREAD_AVAILABLE:
            print("Error: gspread not installed. Run: pip install gspread google-auth")
            return False

        if not self.sheet_id:
            print("Error: GOOGLE_SHEET_ID not configured")
            return False

        creds_dict = get_google_credentials()
        if not creds_dict:
            print("Error: GOOGLE_SHEETS_CREDENTIALS not configured")
            return False

        try:
            credentials = Credentials.from_service_account_info(
                creds_dict,
                scopes=SCOPES
            )
            self._client = gspread.authorize(credentials)
            self._spreadsheet = self._client.open_by_key(self.sheet_id)
            print(f"Connected to Google Sheet: {self._spreadsheet.title}")
            return True
        except Exception as e:
            print(f"Error connecting to Google Sheets: {e}")
            return False

    def _get_worksheet(self, tab_name: str):
        """Get worksheet by name."""
        if tab_name in self._worksheets:
            return self._worksheets[tab_name]

        try:
            worksheet = self._spreadsheet.worksheet(tab_name)
            self._worksheets[tab_name] = worksheet
            return worksheet
        except Exception as e:
            print(f"Error getting worksheet {tab_name}: {e}")
            return None

    def add_candidate(
        self,
        report_id: str,
        candidate_name: str,
        district_id: str,
        filed_date: str,
        ethics_report_url: str,
        is_incumbent: bool = False,
        detected_party: str = "",
        detection_confidence: str = "UNKNOWN",
        detection_source: str = "",
        detection_evidence_url: str = "",
    ) -> dict:
        """
        Add or update a candidate in the Candidates tab.

        Args:
            report_id: Unique ethics report ID
            candidate_name: Candidate name
            district_id: District ID (e.g., "SC-House-091")
            filed_date: Filing date (ISO format)
            ethics_report_url: URL to ethics report
            is_incumbent: Whether candidate is the incumbent
            detected_party: Detected party (D/R/I/O)
            detection_confidence: HIGH/MEDIUM/LOW/UNKNOWN
            detection_source: How party was detected
            detection_evidence_url: URL supporting detection

        Returns:
            dict with action taken
        """
        if not self._spreadsheet:
            if not self.connect():
                return {"action": "error", "error": "Not connected"}

        worksheet = self._get_worksheet(SHEET_TAB_CANDIDATES)
        if not worksheet:
            return {"action": "error", "error": "Candidates tab not found"}

        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Check if candidate already exists by report_id
        existing_row = self._find_row_by_report_id(worksheet, report_id)

        # Build row data matching CANDIDATES_HEADERS order
        row_data = [
            report_id,
            candidate_name,
            district_id,
            filed_date,
            ethics_report_url,
            "Yes" if is_incumbent else "No",
            detected_party,
            detection_confidence,
            detection_source,
            detection_evidence_url,
            "",  # manual_party_override - leave blank
            detected_party,  # final_party - formula would normally handle this
            "",  # party_locked
            now,  # detection_timestamp
            "",  # notes
            now,  # last_synced
        ]

        try:
            if existing_row:
                # Update existing row, but preserve manual_party_override
                existing_values = worksheet.row_values(existing_row)
                if len(existing_values) > 10 and existing_values[10]:  # manual_party_override
                    row_data[10] = existing_values[10]
                    row_data[11] = existing_values[10]  # final_party uses manual override

                worksheet.update(f'A{existing_row}:P{existing_row}', [row_data])
                return {"action": "updated", "row": existing_row}
            else:
                # Append new row
                worksheet.append_row(row_data)
                return {"action": "added"}

        except Exception as e:
            print(f"Error adding candidate: {e}")
            return {"action": "error", "error": str(e)}

    def _find_row_by_report_id(self, worksheet, report_id: str) -> Optional[int]:
        """Find the row number for a candidate by report_id."""
        try:
            cell = worksheet.find(report_id, in_column=1)
            return cell.row if cell else None
        except Exception:
            return None

    def log_sync(
        self,
        event_type: str,
        details: str,
        candidates_added: int = 0,
        candidates_updated: int = 0,
        party_detections: int = 0,
        errors: int = 0,
    ) -> bool:
        """Log a sync operation to the Sync Log tab."""
        if not self._spreadsheet:
            if not self.connect():
                return False

        worksheet = self._get_worksheet(SHEET_TAB_SYNC_LOG)
        if not worksheet:
            return False

        try:
            row_data = [
                datetime.utcnow().isoformat() + "Z",
                event_type,
                details,
                candidates_added,
                candidates_updated,
                party_detections,
                errors,
            ]

            worksheet.append_row(row_data)
            return True

        except Exception as e:
            print(f"Error logging sync: {e}")
            return False


def main():
    """Test the sheets sync."""
    from config import is_google_sheets_configured

    print("Testing Google Sheets Sync")
    print("=" * 60)

    if not is_google_sheets_configured():
        print("Google Sheets not configured. Set GOOGLE_SHEET_ID and GOOGLE_SHEETS_CREDENTIALS")
        return

    sync = SheetsSync()

    if sync.connect():
        print("Connected successfully!")
    else:
        print("Failed to connect")


if __name__ == "__main__":
    main()

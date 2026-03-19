"""
Configuration for SC Ethics Report Monitor with Google Sheets Integration.

Environment Variables:
    RESEND_API_KEY: API key for Resend email service
    SENDGRID_API_KEY: API key for SendGrid email service (fallback)
    NOTIFICATION_EMAIL: Email address(es) for notifications
    FROM_EMAIL: Sender email address
    GOOGLE_SHEETS_CREDENTIALS: Base64-encoded service account JSON or path to JSON file
    GOOGLE_SHEET_ID: ID of the Google Sheet (from URL)
    FIRECRAWL_API_KEY: API key for Firecrawl web scraping
    INCUMBENTS_JSON_PATH: Path to incumbents.json file (optional)
"""

import base64
import json
import os
from pathlib import Path
from typing import Optional


# === Email Configuration ===
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL")
FROM_EMAIL = os.getenv("FROM_EMAIL", "sc-ethics-monitor@example.com")

# === Google Sheets Configuration ===
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_SHEETS_CREDENTIALS_ENV = os.getenv("GOOGLE_SHEETS_CREDENTIALS")

# === Party Detection Configuration ===
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

# === File Paths ===
PROJECT_ROOT = Path(__file__).parent.parent
STATE_FILE = PROJECT_ROOT / "state.json"

# Default path to incumbents.json - can be overridden
INCUMBENTS_JSON_PATH = os.getenv(
    "INCUMBENTS_JSON_PATH",
    str(Path.home() / "Desktop" / "sc-election-map-2026" / "public" / "data" / "incumbents.json")
)

# === Party Detection Constants ===
CONFIDENCE_LEVELS = {
    "HIGH": "HIGH",
    "MEDIUM": "MEDIUM",
    "LOW": "LOW",
    "UNKNOWN": "UNKNOWN"
}

# Fuzzy match threshold (0-100)
FUZZY_MATCH_THRESHOLD = 85

# Party website URLs
SCDP_URL = "https://scdp.org"
SCGOP_URL = "https://scgop.com"
BALLOTPEDIA_BASE_URL = "https://ballotpedia.org"

# === Google Sheets Tab Names ===
# Must match tab names in the Google Sheet (initialized by sc-ethics-monitor)
SHEET_TAB_DISTRICTS = "Districts"
SHEET_TAB_CANDIDATES = "Candidates"
SHEET_TAB_RESEARCH_QUEUE = "Research Queue"
SHEET_TAB_RACE_ANALYSIS = "Race Analysis"
SHEET_TAB_SYNC_LOG = "Sync Log"

# === Column Definitions ===
# Must match structure initialized by sc-ethics-monitor

# Districts tab columns (0-indexed)
DISTRICTS_COLUMNS = {
    "district_id": 0,
    "district_name": 1,
    "chamber": 2,
    "district_number": 3,
    "incumbent_name": 4,
    "incumbent_party": 5,
    "incumbent_since": 6,
    "next_election": 7,
}

DISTRICTS_HEADERS = [
    "district_id",
    "district_name",
    "chamber",
    "district_number",
    "incumbent_name",
    "incumbent_party",
    "incumbent_since",
    "next_election",
]

# Candidates tab columns (0-indexed)
CANDIDATES_COLUMNS = {
    "report_id": 0,
    "candidate_name": 1,
    "district_id": 2,
    "filed_date": 3,
    "ethics_report_url": 4,
    "is_incumbent": 5,
    "detected_party": 6,
    "detection_confidence": 7,
    "detection_source": 8,
    "detection_evidence_url": 9,
    "manual_party_override": 10,
    "final_party": 11,
    "party_locked": 12,
    "detection_timestamp": 13,
    "notes": 14,
    "last_synced": 15,
}

CANDIDATES_HEADERS = [
    "report_id",
    "candidate_name",
    "district_id",
    "filed_date",
    "ethics_report_url",
    "is_incumbent",
    "detected_party",
    "detection_confidence",
    "detection_source",
    "detection_evidence_url",
    "manual_party_override",
    "final_party",
    "party_locked",
    "detection_timestamp",
    "notes",
    "last_synced",
]

# Research Queue columns (0-indexed)
RESEARCH_QUEUE_COLUMNS = {
    "report_id": 0,
    "candidate_name": 1,
    "district_id": 2,
    "detected_party": 3,
    "confidence": 4,
    "suggested_search": 5,
    "scdp_link": 6,
    "scgop_link": 7,
    "status": 8,
    "assigned_to": 9,
    "resolution_notes": 10,
    "resolved_date": 11,
    "added_date": 12,
}

RESEARCH_QUEUE_HEADERS = [
    "report_id",
    "candidate_name",
    "district_id",
    "detected_party",
    "confidence",
    "suggested_search",
    "scdp_link",
    "scgop_link",
    "status",
    "assigned_to",
    "resolution_notes",
    "resolved_date",
    "added_date",
]

# Race Analysis columns (0-indexed)
RACE_ANALYSIS_COLUMNS = {
    "district_id": 0,
    "district_name": 1,
    "incumbent_name": 2,
    "incumbent_party": 3,
    "dem_candidates": 4,
    "rep_candidates": 5,
    "other_candidates": 6,
    "race_status": 7,
    "recruitment_priority": 8,
    "needs_research": 9,
    "last_computed": 10,
}

RACE_ANALYSIS_HEADERS = [
    "district_id",
    "district_name",
    "incumbent_name",
    "incumbent_party",
    "dem_candidates",
    "rep_candidates",
    "other_candidates",
    "race_status",
    "recruitment_priority",
    "needs_research",
    "last_computed",
]

# Sync Log columns (0-indexed)
SYNC_LOG_COLUMNS = {
    "timestamp": 0,
    "event_type": 1,
    "details": 2,
    "candidates_added": 3,
    "candidates_updated": 4,
    "party_detections": 5,
    "errors": 6,
}

SYNC_LOG_HEADERS = [
    "timestamp",
    "event_type",
    "details",
    "candidates_added",
    "candidates_updated",
    "party_detections",
    "errors",
]


def get_google_credentials() -> Optional[dict]:
    """
    Get Google service account credentials.

    Supports:
    1. Base64-encoded JSON in GOOGLE_SHEETS_CREDENTIALS env var
    2. Path to JSON file in GOOGLE_SHEETS_CREDENTIALS env var
    3. Direct JSON string in GOOGLE_SHEETS_CREDENTIALS env var

    Returns:
        dict: Service account credentials or None if not configured
    """
    if not GOOGLE_SHEETS_CREDENTIALS_ENV:
        return None

    # Try as file path first
    cred_path = Path(GOOGLE_SHEETS_CREDENTIALS_ENV)
    if cred_path.exists() and cred_path.is_file():
        try:
            with open(cred_path, "r") as f:
                return json.load(f)
        except Exception:
            pass

    # Try as base64-encoded JSON
    try:
        decoded = base64.b64decode(GOOGLE_SHEETS_CREDENTIALS_ENV)
        return json.loads(decoded)
    except Exception:
        pass

    # Try as direct JSON string
    try:
        return json.loads(GOOGLE_SHEETS_CREDENTIALS_ENV)
    except Exception:
        pass

    return None


def load_incumbents() -> dict:
    """
    Load incumbents data from JSON file or public URL.

    Tries:
    1. Local file path from INCUMBENTS_JSON_PATH
    2. Public URL from sc-election-map-2026 GitHub Pages

    Returns:
        dict: Incumbents data with 'house' and 'senate' keys
    """
    # Try local file first
    try:
        incumbents_path = Path(INCUMBENTS_JSON_PATH)
        if incumbents_path.exists():
            with open(incumbents_path, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load local incumbents.json: {e}")

    # Fallback to public URL
    try:
        import requests
        public_url = "https://russellteter.github.io/sc-election-map-2026/data/incumbents.json"
        response = requests.get(public_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Warning: Could not fetch incumbents.json from public URL: {e}")

    return {"house": {}, "senate": {}}


def is_google_sheets_configured() -> bool:
    """Check if Google Sheets integration is properly configured."""
    return bool(GOOGLE_SHEET_ID and get_google_credentials())


def is_party_detection_configured() -> bool:
    """Check if party detection is properly configured."""
    return bool(FIRECRAWL_API_KEY) or Path(INCUMBENTS_JSON_PATH).exists()


# === Helper Functions ===
def parse_district_from_office(office: str) -> Optional[str]:
    """
    Parse district ID from office string.

    Args:
        office: e.g., "SC House of Representatives District 91" or "SC Senate District 15"

    Returns:
        District ID like "H091" or "S015", or None if not parseable
    """
    import re

    if not office:
        return None

    office_lower = office.lower()

    # House pattern
    house_match = re.search(r'house.*district\s*(\d+)', office_lower)
    if house_match:
        district_num = int(house_match.group(1))
        return f"H{district_num:03d}"

    # Senate pattern
    senate_match = re.search(r'senate.*district\s*(\d+)', office_lower)
    if senate_match:
        district_num = int(senate_match.group(1))
        return f"S{district_num:03d}"

    return None


def get_district_number(office: str) -> Optional[int]:
    """
    Extract just the district number from office string.

    Args:
        office: e.g., "SC House of Representatives District 91"

    Returns:
        District number as integer, or None
    """
    import re

    if not office:
        return None

    match = re.search(r'district\s*(\d+)', office.lower())
    if match:
        return int(match.group(1))
    return None


def is_house_district(office: str) -> bool:
    """Check if office is a House district."""
    if not office:
        return False
    office_lower = office.lower()
    return "house" in office_lower and "district" in office_lower


def is_senate_district(office: str) -> bool:
    """Check if office is a Senate district."""
    if not office:
        return False
    office_lower = office.lower()
    return "senate" in office_lower and "district" in office_lower

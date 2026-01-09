# Function Reference - src/monitor.py

> Complete API documentation for the SC Ethics Filing Monitor core script

---

## Module Overview

**File:** `src/monitor.py`
**Lines:** 364
**Purpose:** Scrape SC Ethics website, detect new campaign disclosure filings, send email notifications

---

## Constants

```python
STATISTICS_API = "https://ethicsfiling.sc.gov/api/Ethics/Get/Public/General/Statistics"
CAMPAIGN_REPORTS_URL = "https://ethicsfiling.sc.gov/public/campaign-reports/reports"
STATE_FILE = Path(__file__).parent.parent / "state.json"
```

## Environment Variables

```python
RESEND_API_KEY = os.getenv("RESEND_API_KEY")       # Primary email provider
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")   # Fallback email provider
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL") # Recipient
FROM_EMAIL = os.getenv("FROM_EMAIL", "sc-ethics-monitor@example.com")
```

---

## Functions

### `log(message: str) -> None`
**Lines:** 31-34

Print timestamped log message to stdout.

```python
log("Starting scrape")
# Output: [2026-01-08 22:28:34 UTC] Starting scrape
```

---

### `get_statistics() -> dict`
**Lines:** 37-45

Fetch current activity statistics from the SC Ethics API.

**Returns:** Dictionary with daily filing counts, or empty dict on error

**Example Response:**
```python
{
    "lastDateOfAnyCandidateReportFilingCount": 100,
    "lastDateOfAnySeiReportFilingCount": 51
}
```

**Usage:** Called at start of main() for logging; not critical to operation.

---

### `extract_report_id(url: str) -> Optional[str]`
**Lines:** 48-51

Extract reportId parameter from a report detail URL.

**Args:**
- `url`: Report URL containing `reportId=XXXXX`

**Returns:** Report ID string or None if not found

**Example:**
```python
extract_report_id("/report-detail?personId=123&reportId=414669")
# Returns: "414669"
```

---

### `scrape_recent_reports(page: Page, max_pages: int = 3) -> list[dict]`
**Lines:** 54-179

Core scraping function. Navigates the SC Ethics website and extracts report data.

**Args:**
- `page`: Playwright Page object
- `max_pages`: Number of results pages to scrape (default: 3, ~45 reports)

**Returns:** List of report dictionaries

**Report Dictionary Schema:**
```python
{
    "report_id": "414669",
    "report_name": "Quarter 4, 2025 Report",
    "candidate_name": "Smith, John",
    "office": "SC House of Representatives District 45",
    "election_year": "2025",
    "election_type": "General",
    "last_updated": "Jan 8, 2026",
    "url": "https://ethicsfiling.sc.gov/public/.../report-detail?...&reportId=414669"
}
```

**Scraping Steps:**
1. Navigate to CAMPAIGN_REPORTS_URL
2. Select current year in Election Year dropdown
3. Click Search button
4. Sort by "Last Updated" descending (click twice)
5. For each page (up to max_pages):
   - Extract all table rows
   - Parse: report link, candidate link, office, year, type, date
   - Extract reportId from URL
6. Click "Next page" if available

**Error Handling:** Logs warnings for individual row failures but continues processing.

---

### `load_state() -> dict`
**Lines:** 182-192

Load previous state from JSON file.

**Returns:** State dictionary with keys:
- `seen_report_ids`: List of previously detected report IDs
- `last_checked`: ISO timestamp of last run

**Default (if file missing/corrupt):**
```python
{"seen_report_ids": [], "last_checked": None}
```

---

### `save_state(state: dict) -> None`
**Lines:** 195-204

Save state to JSON file with updated timestamp.

**Args:**
- `state`: Dictionary containing `seen_report_ids` list

**Side Effects:**
- Updates `state["last_checked"]` to current UTC time
- Writes to STATE_FILE (../state.json relative to script)

---

### `find_new_reports(reports: list[dict], state: dict) -> list[dict]`
**Lines:** 207-211

Find reports that haven't been seen before.

**Args:**
- `reports`: List of report dicts from scrape_recent_reports()
- `state`: State dict containing seen_report_ids

**Returns:** Filtered list containing only new (unseen) reports

**Logic:**
```python
seen_ids = set(state.get("seen_report_ids", []))
return [r for r in reports if r["report_id"] not in seen_ids]
```

---

### `send_email_notification(new_reports: list[dict]) -> bool`
**Lines:** 216-275

Build and send email notification about new reports.

**Args:**
- `new_reports`: List of new report dictionaries

**Returns:** True if email sent successfully, False otherwise

**Behavior:**
1. Check required environment variables (NOTIFICATION_EMAIL, API keys)
2. Build subject line: `"SC Ethics Monitor: {count} New Filing(s) Detected"`
3. Build plain text body (for email clients without HTML)
4. Build HTML body with formatted table
5. Route to `_send_via_resend()` if RESEND_API_KEY set, else `_send_via_sendgrid()`

**Email HTML Structure:**
```html
<h2>SC Ethics Filing Monitor Alert</h2>
<p>Detected <strong>N</strong> new campaign disclosure report(s):</p>
<table>
  <tr><th>Candidate</th><th>Office</th><th>Report</th><th>Updated</th><th>Link</th></tr>
  <!-- One row per report -->
</table>
<p><small>This is an automated notification...</small></p>
```

---

### `_send_via_resend(subject: str, text_content: str, html_content: str) -> bool`
**Lines:** 278-306

Send email via Resend API.

**Args:**
- `subject`: Email subject line
- `text_content`: Plain text body
- `html_content`: HTML body

**Returns:** True on success (HTTP 200/201), False on error

**API Call:**
```python
POST https://api.resend.com/emails
Headers: Authorization: Bearer {RESEND_API_KEY}
Body: {
    "from": FROM_EMAIL,
    "to": [NOTIFICATION_EMAIL],
    "subject": subject,
    "text": text_content,
    "html": html_content
}
```

---

### `_send_via_sendgrid(subject: str, text_content: str, html_content: str) -> bool`
**Lines:** 309-339

Send email via SendGrid API (fallback).

**Args:** Same as `_send_via_resend()`

**Returns:** True on success (HTTP 200/202), False on error

**Note:** SendGrid trial expired Nov 25, 2025. Kept as fallback code.

---

### `main() -> int`
**Lines:** 342-363

Main entry point. Orchestrates the complete monitoring workflow.

**Returns:** Count of new reports detected (0 if none)

**Workflow:**
1. Log startup banner
2. Fetch and log daily statistics (optional)
3. Load previous state
4. Launch Playwright browser (headless Chromium)
5. Call `scrape_recent_reports()` to get current filings
6. Call `find_new_reports()` to identify new ones
7. If new reports found:
   - Log each new report
   - Call `send_email_notification()`
8. Update state with all seen report IDs (union of old + new)
9. Save state to file
10. Log completion banner
11. Return count of new reports

**Exit Codes:**
- Script exits with 0 on success
- Script exits with 1 on scraping failure

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Statistics API fails | Warning logged, continues |
| State file missing | Creates new empty state |
| Individual row parse fails | Warning logged, skips row, continues |
| No reports found | Error logged, exits with code 1 |
| Email send fails | Error logged, continues (state still saved) |
| Browser/scrape fails | Error logged, exits with code 1 |

---

## Type Annotations

```python
from typing import Optional
from playwright.sync_api import Page

def extract_report_id(url: str) -> Optional[str]: ...
def scrape_recent_reports(page: Page, max_pages: int = 3) -> list[dict]: ...
def load_state() -> dict: ...
def save_state(state: dict) -> None: ...
def find_new_reports(reports: list[dict], state: dict) -> list[dict]: ...
def send_email_notification(new_reports: list[dict]) -> bool: ...
def main() -> int: ...
```

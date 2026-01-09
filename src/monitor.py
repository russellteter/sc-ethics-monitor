#!/usr/bin/env python3
"""
SC Ethics Initial Report Monitor

Monitors the SC Ethics Commission website for new Initial Reports filed by
SC House and Senate candidates. Initial Reports are the first campaign finance
disclosure required when a candidate raises or spends $500, indicating serious
intent to run for office.

This tool helps party recruiters identify where candidates are emerging and
where recruitment gaps remain for state legislative seats.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from playwright.sync_api import sync_playwright, Page

# Configuration
STATISTICS_API = "https://ethicsfiling.sc.gov/api/Ethics/Get/Public/General/Statistics"
CAMPAIGN_REPORTS_URL = "https://ethicsfiling.sc.gov/public/campaign-reports/reports"
STATE_FILE = Path(__file__).parent.parent / "state.json"

# Email configuration (from environment variables)
# Supports both Resend (preferred) and SendGrid
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL")
FROM_EMAIL = os.getenv("FROM_EMAIL", "sc-ethics-monitor@example.com")

# Office type patterns for filtering to SC House and Senate only
HOUSE_SENATE_PATTERNS = [
    "house of representatives",
    "sc house",
    "state house",
    "senate",
    "sc senate",
    "state senate",
]


def is_house_or_senate(office_text: str) -> bool:
    """Check if the office is SC House or Senate (not County, Municipal, etc.)."""
    if not office_text:
        return False
    office_lower = office_text.lower()
    return any(pattern in office_lower for pattern in HOUSE_SENATE_PATTERNS)


def log(message: str) -> None:
    """Print timestamped log message."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{timestamp}] {message}")


def get_statistics() -> dict:
    """Fetch current activity statistics from the API."""
    try:
        response = requests.get(STATISTICS_API, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log(f"Warning: Could not fetch statistics: {e}")
        return {}


def extract_report_id(url: str) -> Optional[str]:
    """Extract reportId from a report detail URL."""
    match = re.search(r'reportId=(\d+)', url)
    return match.group(1) if match else None


def scrape_recent_reports(page: Page, max_pages: int = 3) -> list[dict]:
    """
    Scrape recent campaign reports from the website.

    Args:
        page: Playwright page object
        max_pages: Maximum number of pages to scrape (default 3, ~45 reports)

    Returns:
        List of report dictionaries with filing details
    """
    reports = []

    log(f"Navigating to {CAMPAIGN_REPORTS_URL}")
    page.goto(CAMPAIGN_REPORTS_URL)
    page.wait_for_load_state("networkidle")

    # Select current year for election year filter
    current_year = str(datetime.now().year)
    log(f"Setting election year filter to {current_year}")

    try:
        # Click the election year dropdown
        year_dropdown = page.get_by_title("Election Year dropdown").get_by_role("listbox")
        year_dropdown.click()
        page.wait_for_timeout(500)

        # Select current year
        page.get_by_role("option", name=current_year).click()
        page.wait_for_timeout(500)
    except Exception as e:
        log(f"Warning: Could not set year filter: {e}")

    # Select "Initial" report type to find new candidates
    log("Setting report type filter to 'Initial'")
    try:
        report_type_dropdown = page.get_by_title("Report Name dropdown").get_by_role("listbox")
        report_type_dropdown.click()
        page.wait_for_timeout(500)
        page.get_by_role("option", name="Initial").click()
        page.wait_for_timeout(500)
    except Exception as e:
        log(f"Warning: Could not set report type filter: {e}")

    # Click search
    log("Executing search...")
    page.get_by_role("button", name="Search").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    # Check if we got results
    try:
        status_text = page.locator("status").first.text_content()
        if "No entries" in status_text:
            log("No reports found for current year filter")
            return reports
        log(f"Search status: {status_text}")
    except Exception:
        pass

    # Sort by Last Updated (descending) to get most recent first
    log("Sorting by Last Updated (descending)...")
    try:
        # Click twice to get descending order
        last_updated_header = page.get_by_text("Last Updated").first
        last_updated_header.click()
        page.wait_for_timeout(500)
        last_updated_header.click()
        page.wait_for_timeout(1000)
    except Exception as e:
        log(f"Warning: Could not sort by Last Updated: {e}")

    # Scrape multiple pages
    for page_num in range(max_pages):
        log(f"Scraping page {page_num + 1}...")

        # Extract report data from current page
        rows = page.locator("table").last.locator("tr")
        row_count = rows.count()

        for i in range(row_count):
            try:
                row = rows.nth(i)
                cells = row.locator("td, gridcell")

                if cells.count() < 6:
                    continue

                # Extract report link and details
                report_link = row.locator("a").first
                report_url = report_link.get_attribute("href") or ""
                report_name = report_link.text_content() or ""

                # Get candidate name (second link in row)
                candidate_link = row.locator("a").nth(1)
                candidate_name = candidate_link.text_content() or ""

                # Get other fields
                office = cells.nth(2).text_content() or ""
                election_year = cells.nth(3).text_content() or ""
                election_type = cells.nth(4).text_content() or ""
                last_updated = cells.nth(5).text_content() or ""

                # Extract report ID for unique identification
                report_id = extract_report_id(report_url)

                if report_id:
                    reports.append({
                        "report_id": report_id,
                        "report_name": report_name.strip(),
                        "candidate_name": candidate_name.strip(),
                        "office": office.strip(),
                        "election_year": election_year.strip(),
                        "election_type": election_type.strip(),
                        "last_updated": last_updated.strip(),
                        "url": f"https://ethicsfiling.sc.gov{report_url}" if report_url.startswith("/") else report_url
                    })
            except Exception as e:
                log(f"Warning: Error extracting row {i}: {e}")
                continue

        # Try to go to next page if not on last page
        if page_num < max_pages - 1:
            try:
                next_button = page.get_by_title("Go to the next page")
                if next_button.is_enabled():
                    next_button.click()
                    page.wait_for_timeout(1000)
                else:
                    log("No more pages available")
                    break
            except Exception:
                log("No more pages available")
                break

    log(f"Scraped {len(reports)} reports total")
    return reports


def load_state() -> dict:
    """Load previous state from JSON file."""
    if not STATE_FILE.exists():
        return {"seen_report_ids": [], "last_checked": None}

    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        log(f"Warning: Could not load state file: {e}")
        return {"seen_report_ids": [], "last_checked": None}


def save_state(state: dict) -> None:
    """Save state to JSON file."""
    state["last_checked"] = datetime.utcnow().isoformat() + "Z"

    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
        log(f"State saved with {len(state.get('seen_report_ids', []))} tracked reports")
    except Exception as e:
        log(f"Error saving state: {e}")


def find_new_reports(reports: list[dict], state: dict) -> list[dict]:
    """Find Initial Reports for House/Senate that haven't been seen before."""
    seen_ids = set(state.get("seen_report_ids", []))

    new_reports = []
    filtered_out = 0

    for r in reports:
        if r["report_id"] in seen_ids:
            continue

        # Filter to only SC House and Senate candidates
        if not is_house_or_senate(r.get("office", "")):
            filtered_out += 1
            continue

        new_reports.append(r)

    if filtered_out > 0:
        log(f"Filtered out {filtered_out} non-House/Senate reports")

    return new_reports


def send_email_notification(new_reports: list[dict]) -> bool:
    """Send email notification about new Initial Reports via Resend or SendGrid."""
    if not NOTIFICATION_EMAIL:
        log("Email not configured - NOTIFICATION_EMAIL not set")
        return False

    if not RESEND_API_KEY and not SENDGRID_API_KEY:
        log("Email not configured - set RESEND_API_KEY or SENDGRID_API_KEY")
        return False

    # Build email content - focused on Initial Reports for candidate tracking
    count = len(new_reports)
    subject = f"NEW CANDIDATE ALERT: {count} Initial Report{'s' if count > 1 else ''} Filed"

    # Plain text version - clear format for quick scanning
    text_content = "=" * 50 + "\n"
    text_content += "NEW CANDIDATE INITIAL REPORT DETECTED\n"
    text_content += "=" * 50 + "\n\n"

    for report in new_reports:
        text_content += f"Candidate:  {report['candidate_name']}\n"
        text_content += f"Office:     {report['office']}\n"
        text_content += f"Report:     {report['report_name']}\n"
        text_content += f"Filed:      {report['last_updated']}\n"
        text_content += f"\nView Report:\n{report['url']}\n"
        text_content += "\n" + "-" * 50 + "\n\n"

    text_content += "This indicates the candidate has raised or spent\n"
    text_content += "at least $500 and filed their first required\n"
    text_content += "campaign disclosure.\n"

    # HTML version - clean table format
    html_content = """
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto;">
    <div style="background-color: #1a365d; color: white; padding: 20px; text-align: center;">
        <h1 style="margin: 0;">NEW CANDIDATE INITIAL REPORT</h1>
    </div>
    """

    for report in new_reports:
        html_content += f"""
        <div style="border: 1px solid #ddd; margin: 20px 0; padding: 20px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; width: 120px; font-weight: bold; color: #555;">Candidate:</td>
                    <td style="padding: 8px 0; font-size: 18px;">{report['candidate_name']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold; color: #555;">Office:</td>
                    <td style="padding: 8px 0;">{report['office']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold; color: #555;">Report:</td>
                    <td style="padding: 8px 0;">{report['report_name']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold; color: #555;">Filed:</td>
                    <td style="padding: 8px 0;">{report['last_updated']}</td>
                </tr>
            </table>
            <div style="margin-top: 15px;">
                <a href="{report['url']}" style="background-color: #2563eb; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View Report</a>
            </div>
        </div>
        """

    html_content += """
    <div style="background-color: #f0f4f8; padding: 15px; margin-top: 20px; border-left: 4px solid #2563eb;">
        <p style="margin: 0; color: #555;">
            <strong>What this means:</strong> This candidate has raised or spent at least $500
            and filed their first required campaign disclosure - indicating serious intent to run.
        </p>
    </div>
    <p style="color: #888; font-size: 12px; margin-top: 20px;">
        SC Ethics Initial Report Monitor - Tracking new candidate filings for SC House & Senate
    </p>
    </body>
    </html>
    """

    # Try Resend first (preferred), fall back to SendGrid
    if RESEND_API_KEY:
        return _send_via_resend(subject, text_content, html_content)
    else:
        return _send_via_sendgrid(subject, text_content, html_content)


def _send_via_resend(subject: str, text_content: str, html_content: str) -> bool:
    """Send email via Resend API."""
    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "from": FROM_EMAIL,
                "to": [NOTIFICATION_EMAIL],
                "subject": subject,
                "text": text_content,
                "html": html_content
            },
            timeout=30
        )

        if response.status_code in [200, 201]:
            log(f"Email sent successfully via Resend to {NOTIFICATION_EMAIL}")
            return True
        else:
            log(f"Resend failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        log(f"Error sending via Resend: {e}")
        return False


def _send_via_sendgrid(subject: str, text_content: str, html_content: str) -> bool:
    """Send email via SendGrid API."""
    try:
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {SENDGRID_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "personalizations": [{"to": [{"email": NOTIFICATION_EMAIL}]}],
                "from": {"email": FROM_EMAIL},
                "subject": subject,
                "content": [
                    {"type": "text/plain", "value": text_content},
                    {"type": "text/html", "value": html_content}
                ]
            },
            timeout=30
        )

        if response.status_code in [200, 202]:
            log(f"Email sent successfully via SendGrid to {NOTIFICATION_EMAIL}")
            return True
        else:
            log(f"SendGrid failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        log(f"Error sending via SendGrid: {e}")
        return False


def main():
    """
    Main monitoring function.

    Detects new Initial Reports filed by SC House and Senate candidates.
    Initial Reports indicate serious candidates who have raised/spent $500+.
    """
    log("=" * 60)
    log("SC Ethics Initial Report Monitor - Starting")
    log("Tracking: SC House & Senate candidates filing Initial Reports")
    log("=" * 60)

    # Get current statistics
    stats = get_statistics()
    if stats:
        log(f"Today's activity: {stats.get('lastDateOfAnyCandidateReportFilingCount', 'N/A')} campaign reports, "
            f"{stats.get('lastDateOfAnySeiReportFilingCount', 'N/A')} SEI reports")

    # Load previous state
    state = load_state()
    if state.get("last_checked"):
        log(f"Last check: {state['last_checked']}")
    else:
        log("First run - will establish baseline")

    # Scrape Initial Reports
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            reports = scrape_recent_reports(page, max_pages=3)

            browser.close()
    except Exception as e:
        log(f"Error during scraping: {e}")
        sys.exit(1)

    if not reports:
        log("No Initial Reports found for current year")
        # Not an error - there may simply be no Initial Reports yet
        save_state(state)
        return 0

    log(f"Found {len(reports)} Initial Report(s) total")

    # Find new House/Senate Initial Reports
    new_reports = find_new_reports(reports, state)

    if new_reports:
        log(f"NEW: {len(new_reports)} House/Senate Initial Report(s)!")
        for report in new_reports:
            log(f"  - {report['candidate_name']} ({report['office']})")

        # Send notification
        send_email_notification(new_reports)
    else:
        log("No new reports detected")

    # Update state with all seen report IDs
    all_report_ids = list(set(
        state.get("seen_report_ids", []) +
        [r["report_id"] for r in reports]
    ))
    state["seen_report_ids"] = all_report_ids
    save_state(state)

    log("=" * 60)
    log("SC Ethics Initial Report Monitor - Complete")
    log("=" * 60)

    return len(new_reports)


if __name__ == "__main__":
    sys.exit(0 if main() >= 0 else 1)

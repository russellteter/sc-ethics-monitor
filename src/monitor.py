#!/usr/bin/env python3
"""
SC Ethics Filing Monitor

Monitors the SC Ethics Commission website for new campaign disclosure reports
and sends email notifications when new filings are detected.
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

# SendGrid configuration (from environment variables)
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL")
FROM_EMAIL = os.getenv("FROM_EMAIL", "sc-ethics-monitor@example.com")


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
    """Find reports that haven't been seen before."""
    seen_ids = set(state.get("seen_report_ids", []))
    new_reports = [r for r in reports if r["report_id"] not in seen_ids]
    return new_reports


def send_email_notification(new_reports: list[dict]) -> bool:
    """Send email notification about new reports via SendGrid."""
    if not SENDGRID_API_KEY or not NOTIFICATION_EMAIL:
        log("Email not configured - skipping notification")
        log("Set SENDGRID_API_KEY and NOTIFICATION_EMAIL environment variables")
        return False

    # Build email content
    subject = f"SC Ethics Monitor: {len(new_reports)} New Filing(s) Detected"

    # Plain text version
    text_content = f"SC Ethics Filing Monitor has detected {len(new_reports)} new campaign disclosure report(s).\n\n"
    for report in new_reports:
        text_content += f"- {report['candidate_name']} ({report['office']})\n"
        text_content += f"  Report: {report['report_name']}\n"
        text_content += f"  Updated: {report['last_updated']}\n"
        text_content += f"  Link: {report['url']}\n\n"

    # HTML version
    html_content = f"""
    <html>
    <body>
    <h2>SC Ethics Filing Monitor Alert</h2>
    <p>Detected <strong>{len(new_reports)}</strong> new campaign disclosure report(s):</p>
    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse;">
        <tr style="background-color: #f0f0f0;">
            <th>Candidate</th>
            <th>Office</th>
            <th>Report</th>
            <th>Updated</th>
            <th>Link</th>
        </tr>
    """

    for report in new_reports:
        html_content += f"""
        <tr>
            <td>{report['candidate_name']}</td>
            <td>{report['office']}</td>
            <td>{report['report_name']}</td>
            <td>{report['last_updated']}</td>
            <td><a href="{report['url']}">View</a></td>
        </tr>
        """

    html_content += """
    </table>
    <p><small>This is an automated notification from SC Ethics Filing Monitor.</small></p>
    </body>
    </html>
    """

    # Send via SendGrid API
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
            log(f"Email notification sent successfully to {NOTIFICATION_EMAIL}")
            return True
        else:
            log(f"Email send failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        log(f"Error sending email: {e}")
        return False


def main():
    """Main monitoring function."""
    log("=" * 60)
    log("SC Ethics Filing Monitor - Starting")
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

    # Scrape recent reports
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
        log("No reports found - check if website structure has changed")
        sys.exit(1)

    # Find new reports
    new_reports = find_new_reports(reports, state)

    if new_reports:
        log(f"Found {len(new_reports)} NEW report(s)!")
        for report in new_reports:
            log(f"  - {report['candidate_name']} ({report['office']}): {report['report_name']}")

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
    log("SC Ethics Filing Monitor - Complete")
    log("=" * 60)

    return len(new_reports)


if __name__ == "__main__":
    sys.exit(0 if main() >= 0 else 1)

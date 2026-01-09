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
from datetime import datetime, timedelta
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


def parse_date(date_str: str) -> str:
    """Convert 'Jan 8, 2026' to '2026-01-08' for consistent sorting."""
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str.strip(), "%b %d, %Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return date_str


def format_date_display(iso_date: str) -> str:
    """Convert '2026-01-08' to 'Jan 8, 2026' for display."""
    if not iso_date:
        return ""
    try:
        dt = datetime.strptime(iso_date, "%Y-%m-%d")
        return dt.strftime("%b %d, %Y")
    except ValueError:
        return iso_date


def get_last_30_days(reports_metadata: dict) -> list[dict]:
    """Get reports from last 30 days, sorted by date descending."""
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    results = [
        {"report_id": rid, **meta}
        for rid, meta in reports_metadata.items()
        if meta.get("filed_date", "") >= cutoff
    ]
    return sorted(results, key=lambda r: r.get("filed_date", ""), reverse=True)


def get_subject_line(new_count: int) -> str:
    """Generate context-specific email subject line."""
    if new_count > 0:
        s = "s" if new_count > 1 else ""
        return f"South Carolina Ethics Monitor: {new_count} New Statehouse Candidate{s} Today"
    return "South Carolina Ethics Monitor: Daily Statehouse Candidate Digest"


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


def scrape_recent_reports(page: Page, max_pages: int = 3, election_year: Optional[str] = None) -> list[dict]:
    """
    Scrape recent campaign reports from the website.

    Args:
        page: Playwright page object
        max_pages: Maximum number of pages to scrape (default 3, ~45 reports)
        election_year: Specific year to filter (default: current year)

    Returns:
        List of report dictionaries with filing details
    """
    reports = []

    log(f"Navigating to {CAMPAIGN_REPORTS_URL}")
    page.goto(CAMPAIGN_REPORTS_URL)
    page.wait_for_load_state("networkidle")

    # Select election year filter
    target_year = election_year or str(datetime.now().year)
    log(f"Setting election year filter to {target_year}")

    try:
        # Click the election year dropdown
        year_dropdown = page.get_by_title("Election Year dropdown").get_by_role("listbox")
        year_dropdown.click()
        page.wait_for_timeout(500)

        # Select target year
        page.get_by_role("option", name=target_year).click()
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


def scrape_2025_calendar_year(page: Page, state: dict) -> dict:
    """
    Scrape ALL Initial Reports FILED in calendar year 2025 (Jan 1 - Dec 31).

    IMPORTANT: This filters by FILING DATE (when the report was submitted),
    NOT by election year (which election cycle the report is for).

    Strategy:
    - Scrape multiple election years (2024, 2025, 2026) to capture all filings
    - Filter client-side by filed_date to keep only 2025 calendar year filings
    - This ensures we get Dec 2025 filings for 2024 cycle AND exclude Jan 2026 filings

    Returns dict of report metadata keyed by report_id.
    """
    log("Scraping Initial Reports filed in calendar year 2025...")

    # Scrape multiple election years to catch all possible 2025 filings
    # - 2024 cycle: May have late filings in early 2025
    # - 2025 cycle: Main target, but election_year filter != filing date
    # - 2026 cycle: May have early filings in late 2025
    all_reports = []
    for election_year in ["2024", "2025", "2026"]:
        log(f"  Scraping election year {election_year}...")
        try:
            reports = scrape_recent_reports(page, max_pages=15, election_year=election_year)
            all_reports.extend(reports)
            log(f"    Found {len(reports)} reports for {election_year} cycle")
        except Exception as e:
            log(f"    Warning: Could not scrape {election_year}: {e}")

    # Deduplicate by report_id (same report might appear in multiple years)
    seen_ids = set()
    unique_reports = []
    for r in all_reports:
        if r["report_id"] not in seen_ids:
            seen_ids.add(r["report_id"])
            unique_reports.append(r)

    log(f"  Total unique reports across all years: {len(unique_reports)}")

    # Filter to: House/Senate AND filed in calendar year 2025
    historical = {}
    excluded_wrong_date = 0
    excluded_wrong_office = 0

    for r in unique_reports:
        # Must be House/Senate
        if not is_house_or_senate(r.get("office", "")):
            excluded_wrong_office += 1
            continue

        # Parse the filing date
        filed_date = parse_date(r["last_updated"])

        # CRITICAL: Filter by FILING DATE, not election year
        # Only keep reports filed in 2025 (YYYY-MM-DD format starts with "2025-")
        if not filed_date.startswith("2025-"):
            excluded_wrong_date += 1
            continue

        historical[r["report_id"]] = {
            "candidate_name": r["candidate_name"],
            "office": r["office"],
            "election_year": r["election_year"],  # Keep for context
            "report_name": r["report_name"],
            "filed_date": filed_date,
            "url": r["url"]
        }

    log(f"  Filtered: {excluded_wrong_office} non-House/Senate, {excluded_wrong_date} not filed in 2025")
    log(f"  Result: {len(historical)} House/Senate Initial Reports filed in 2025")
    return historical


def load_state() -> dict:
    """Load previous state from JSON file with backward compatibility."""
    default_state = {
        "seen_report_ids": [],
        "last_checked": None,
        "reports_with_metadata": {},
        "historical_2025": {"cached_date": None, "reports": {}}
    }

    if not STATE_FILE.exists():
        return default_state

    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)

        # Ensure new fields exist (backward compatibility)
        if "reports_with_metadata" not in state:
            state["reports_with_metadata"] = {}
        if "historical_2025" not in state:
            state["historical_2025"] = {"cached_date": None, "reports": {}}

        return state
    except Exception as e:
        log(f"Warning: Could not load state file: {e}")
        return default_state


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


def send_daily_digest(
    new_reports: list[dict],
    last_30_days: list[dict],
    historical_2025: dict,
    total_tracked: int
) -> bool:
    """
    Send daily digest email with new candidates, 30-day history, and 2025 data.
    Always sends, even if no new candidates detected.
    """
    if not NOTIFICATION_EMAIL:
        log("Email not configured - NOTIFICATION_EMAIL not set")
        return False

    if not RESEND_API_KEY and not SENDGRID_API_KEY:
        log("Email not configured - set RESEND_API_KEY or SENDGRID_API_KEY")
        return False

    # Generate subject line based on new candidates
    subject = get_subject_line(len(new_reports))
    today_str = datetime.now().strftime("%B %d, %Y")

    # === PLAIN TEXT VERSION ===
    text_content = "=" * 60 + "\n"
    text_content += "SOUTH CAROLINA STATEHOUSE CANDIDATE MONITOR\n"
    text_content += f"Daily Digest - {today_str}\n"
    text_content += "=" * 60 + "\n\n"

    # Section 1: New Candidates Today
    text_content += "NEW CANDIDATES TODAY\n"
    text_content += "-" * 40 + "\n"
    if new_reports:
        for r in new_reports:
            text_content += f"\n  {r['candidate_name']}\n"
            text_content += f"  Office: {r['office']}\n"
            text_content += f"  Filed: {r.get('last_updated', 'N/A')}\n"
            text_content += f"  {r['url']}\n"
    else:
        text_content += "\nNo new candidates in the last 24 hours.\n"
    text_content += "\n"

    # Section 2: Last 30 Days
    text_content += "LAST 30 DAYS\n"
    text_content += "-" * 40 + "\n"
    if last_30_days:
        for r in last_30_days[:15]:  # Limit to 15 for readability
            date_display = format_date_display(r.get("filed_date", ""))
            text_content += f"  {date_display}: {r['candidate_name']} - {r['office']}\n"
        if len(last_30_days) > 15:
            text_content += f"  ... and {len(last_30_days) - 15} more\n"
    else:
        text_content += "  No filings in the last 30 days.\n"
    text_content += "\n"

    # Section 3: 2025 Historical
    text_content += "INITIAL REPORTS FILED IN 2025\n"
    text_content += "-" * 40 + "\n"
    text_content += f"  {len(historical_2025)} candidates tracked\n"
    text_content += "\n"

    text_content += "=" * 60 + "\n"
    text_content += "SC Ethics Initial Report Monitor\n"
    text_content += "Tracking candidates who have raised/spent $500+\n"

    # === HTML VERSION ===
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; margin: 0; padding: 0; background-color: #f8fafc; }}
            .container {{ max-width: 680px; margin: 0 auto; background: white; }}
            .header {{ background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); color: white; padding: 24px 20px; text-align: center; }}
            .header h1 {{ margin: 0 0 8px 0; font-size: 22px; font-weight: 600; }}
            .header p {{ margin: 0; opacity: 0.9; font-size: 14px; }}
            .section {{ padding: 20px; border-bottom: 1px solid #e2e8f0; }}
            .section-header {{ font-size: 16px; font-weight: 600; color: #1e293b; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }}
            .section-header .badge {{ background: #10b981; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 500; }}
            .no-new {{ color: #64748b; font-style: italic; padding: 12px 0; }}
            .candidate-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 12px; }}
            .candidate-card.new {{ border-left: 4px solid #10b981; }}
            .candidate-name {{ font-size: 17px; font-weight: 600; color: #1e293b; margin-bottom: 4px; }}
            .candidate-office {{ color: #64748b; font-size: 14px; margin-bottom: 8px; }}
            .candidate-date {{ color: #94a3b8; font-size: 13px; }}
            .view-link {{ display: inline-block; margin-top: 10px; background: #2563eb; color: white; padding: 8px 16px; text-decoration: none; border-radius: 6px; font-size: 13px; font-weight: 500; }}
            .view-link:hover {{ background: #1d4ed8; }}
            table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
            th {{ text-align: left; padding: 10px 8px; background: #f1f5f9; color: #475569; font-weight: 600; border-bottom: 2px solid #e2e8f0; }}
            td {{ padding: 10px 8px; border-bottom: 1px solid #e2e8f0; color: #334155; }}
            td a {{ color: #2563eb; text-decoration: none; }}
            td a:hover {{ text-decoration: underline; }}
            .stats-box {{ background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 16px; text-align: center; }}
            .stats-number {{ font-size: 32px; font-weight: 700; color: #1e40af; }}
            .stats-label {{ color: #64748b; font-size: 14px; margin-top: 4px; }}
            .footer {{ padding: 20px; text-align: center; color: #94a3b8; font-size: 12px; background: #f8fafc; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>South Carolina Statehouse Candidate Monitor</h1>
                <p>Daily Digest &mdash; {today_str}</p>
            </div>
    """

    # Section 1: New Candidates Today
    html_content += '<div class="section">'
    if new_reports:
        html_content += f'<div class="section-header">New Candidates Today <span class="badge">{len(new_reports)}</span></div>'
        for r in new_reports:
            filed = r.get('last_updated', 'N/A')
            html_content += f'''
            <div class="candidate-card new">
                <div class="candidate-name">{r['candidate_name']}</div>
                <div class="candidate-office">{r['office']}</div>
                <div class="candidate-date">Filed: {filed}</div>
                <a href="{r['url']}" class="view-link">View Report</a>
            </div>
            '''
    else:
        html_content += '<div class="section-header">New Candidates Today</div>'
        html_content += '<p class="no-new">No new candidates in the last 24 hours.</p>'
    html_content += '</div>'

    # Section 2: Last 30 Days
    html_content += '<div class="section">'
    html_content += f'<div class="section-header">Last 30 Days</div>'
    if last_30_days:
        html_content += '''
        <table>
            <thead>
                <tr><th>Date</th><th>Candidate</th><th>Office</th></tr>
            </thead>
            <tbody>
        '''
        for r in last_30_days[:20]:  # Limit to 20 rows
            date_display = format_date_display(r.get("filed_date", ""))
            html_content += f'''
                <tr>
                    <td>{date_display}</td>
                    <td><a href="{r.get('url', '#')}">{r['candidate_name']}</a></td>
                    <td>{r['office']}</td>
                </tr>
            '''
        html_content += '</tbody></table>'
        if len(last_30_days) > 20:
            html_content += f'<p style="color: #64748b; font-size: 13px; margin-top: 8px;">... and {len(last_30_days) - 20} more</p>'
    else:
        html_content += '<p class="no-new">No filings in the last 30 days.</p>'
    html_content += '</div>'

    # Section 3: 2025 Historical Summary
    html_content += '<div class="section">'
    html_content += '<div class="section-header">Initial Reports Filed in 2025</div>'
    html_content += f'''
    <div class="stats-box">
        <div class="stats-number">{len(historical_2025)}</div>
        <div class="stats-label">House/Senate candidates filed Initial Reports during 2025</div>
    </div>
    '''

    # Show a compact table of 2025 candidates
    if historical_2025:
        sorted_2025 = sorted(
            [{"report_id": k, **v} for k, v in historical_2025.items()],
            key=lambda x: x.get("filed_date", ""),
            reverse=True
        )
        html_content += '''
        <table style="margin-top: 16px;">
            <thead>
                <tr><th>Date</th><th>Candidate</th><th>Office</th></tr>
            </thead>
            <tbody>
        '''
        for r in sorted_2025[:30]:  # Show up to 30
            date_display = format_date_display(r.get("filed_date", ""))
            html_content += f'''
                <tr>
                    <td>{date_display}</td>
                    <td><a href="{r.get('url', '#')}">{r['candidate_name']}</a></td>
                    <td>{r['office']}</td>
                </tr>
            '''
        html_content += '</tbody></table>'
        if len(sorted_2025) > 30:
            html_content += f'<p style="color: #64748b; font-size: 13px; margin-top: 8px;">... and {len(sorted_2025) - 30} more</p>'

    html_content += '</div>'

    # Footer
    html_content += '''
            <div class="footer">
                <p><strong>SC Ethics Initial Report Monitor</strong></p>
                <p>Tracking SC House &amp; Senate candidates who have raised or spent $500+</p>
            </div>
        </div>
    </body>
    </html>
    '''

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
    Main monitoring function - Daily Digest Mode.

    Sends a daily digest email with:
    1. New candidates detected in the last 24 hours
    2. All candidates from the last 30 days
    3. All 2025 statehouse candidates (cached)

    Always sends email, even if no new candidates detected.
    """
    log("=" * 60)
    log("SC Ethics Initial Report Monitor - Daily Digest")
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

    # Scrape Initial Reports for current year
    historical_2025 = {}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Scrape current year Initial Reports
            reports = scrape_recent_reports(page, max_pages=5)

            # Scrape/refresh 2025 historical data (cached)
            historical_2025 = scrape_2025_calendar_year(page, state)

            browser.close()
    except Exception as e:
        log(f"Error during scraping: {e}")
        sys.exit(1)

    log(f"Found {len(reports)} Initial Report(s) for current year")

    # Find new House/Senate Initial Reports
    new_reports = find_new_reports(reports, state)

    if new_reports:
        log(f"NEW: {len(new_reports)} House/Senate Initial Report(s)!")
        for report in new_reports:
            log(f"  - {report['candidate_name']} ({report['office']})")
    else:
        log("No new reports detected")

    # Update state with report IDs and metadata
    all_report_ids = list(set(
        state.get("seen_report_ids", []) +
        [r["report_id"] for r in reports]
    ))
    state["seen_report_ids"] = all_report_ids

    # Store metadata for House/Senate reports (for 30-day history)
    reports_metadata = state.get("reports_with_metadata", {})
    for r in reports:
        if is_house_or_senate(r.get("office", "")):
            reports_metadata[r["report_id"]] = {
                "candidate_name": r["candidate_name"],
                "office": r["office"],
                "report_name": r["report_name"],
                "filed_date": parse_date(r["last_updated"]),
                "url": r["url"]
            }
    state["reports_with_metadata"] = reports_metadata

    # Update 2025 cache
    state["historical_2025"] = {
        "cached_date": datetime.utcnow().isoformat() + "Z",
        "reports": historical_2025
    }

    # Calculate last 30 days from metadata
    last_30_days = get_last_30_days(reports_metadata)
    log(f"Last 30 days: {len(last_30_days)} House/Senate filings")
    log(f"2025 historical: {len(historical_2025)} House/Senate filings")

    # ALWAYS send daily digest (not conditional)
    log("Sending daily digest email...")
    send_daily_digest(
        new_reports=new_reports,
        last_30_days=last_30_days,
        historical_2025=historical_2025,
        total_tracked=len(reports_metadata)
    )

    # Save state
    save_state(state)

    log("=" * 60)
    log("SC Ethics Initial Report Monitor - Complete")
    log("=" * 60)

    return len(new_reports)


if __name__ == "__main__":
    sys.exit(0 if main() >= 0 else 1)

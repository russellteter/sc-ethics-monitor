#!/usr/bin/env python3
"""
SC Ethics Initial Report Monitor

Monitors the SC Ethics Commission website for new Initial Reports filed by
SC House of Representatives candidates. Initial Reports are the first campaign
finance disclosure required when a candidate raises or spends $500, indicating
serious intent to run for office.

This tool helps party recruiters identify where candidates are emerging and
where recruitment gaps remain across 124 SC House districts.

Enhanced with:
- Party affiliation detection (incumbent matching, web sources)
- Google Sheets sync for centralized tracking
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
from playwright.sync_api import sync_playwright, Page

# Party detection and sheets sync (optional - gracefully degrade if not available)
try:
    from party_detector import detect_party, PartyResult
    PARTY_DETECTION_AVAILABLE = True
except ImportError:
    PARTY_DETECTION_AVAILABLE = False
    PartyResult = None

try:
    from sheets_sync import SheetsSync
    SHEETS_SYNC_AVAILABLE = True
except ImportError:
    SHEETS_SYNC_AVAILABLE = False

try:
    from config import parse_district_from_office
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    def parse_district_from_office(office: str) -> Optional[str]:
        """Fallback district parser - returns district ID like H091."""
        if not office:
            return None
        office_lower = office.lower()
        match = re.search(r'district\s*(\d+)', office_lower)
        if not match:
            return None
        district_num = int(match.group(1))
        if 'house' in office_lower:
            return f"H{district_num:03d}"
        return None

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

# Office type patterns for filtering to SC House of Representatives only
STATE_HOUSE_PATTERNS = [
    "sc house of representatives",
    "house of representatives district",
]


def is_state_house(office_text: str) -> bool:
    """Check if the office is SC House of Representatives only."""
    if not office_text:
        return False
    office_lower = office_text.lower()
    return any(pattern in office_lower for pattern in STATE_HOUSE_PATTERNS)


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


def format_date_compact(iso_date: str) -> str:
    """Convert '2026-01-08' to 'Jan 08' for compact table display."""
    if not iso_date:
        return ""
    try:
        dt = datetime.strptime(iso_date, "%Y-%m-%d")
        return dt.strftime("%b %d")
    except ValueError:
        return iso_date


def abbreviate_office(office: str) -> str:
    """Shorten office names for compact table display."""
    if not office:
        return ""
    return office.replace("SC House of Representatives District ", "District ")


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
    date_str = datetime.now().strftime("%-m/%-d")
    if new_count > 0:
        s = "s" if new_count > 1 else ""
        return f"SC House Candidate Filings Report - {new_count} New Candidate{s} Today - {date_str}"
    return f"SC House Candidate Filings Report - No New Filings - {date_str}"


# Email template selection: "A" = Daily Brief, "B" = Intelligence Digest
EMAIL_TEMPLATE = os.getenv("EMAIL_TEMPLATE", "A")


def format_candidate_name(name: str) -> str:
    """Convert 'Last, First M' to 'First M Last'."""
    if not name:
        return ""
    if ", " not in name:
        return name.strip()
    parts = name.split(", ", 1)
    return f"{parts[1].strip()} {parts[0].strip()}"


def format_district(office: str) -> str:
    """Extract 'District 91' from 'SC House of Representatives District 91'."""
    if not office:
        return ""
    match = re.search(r'District\s*(\d+)', office, re.IGNORECASE)
    if match:
        return f"District {match.group(1)}"
    return office


def _party_badge_html(party: str) -> str:
    """Generate inline HTML party badge."""
    if party == "D":
        return '<span style="display:inline-block;background:#2563eb;color:#fff;padding:1px 7px;border-radius:3px;font-size:11px;font-weight:700;letter-spacing:0.03em;">D</span>'
    elif party == "R":
        return '<span style="display:inline-block;background:#dc2626;color:#fff;padding:1px 7px;border-radius:3px;font-size:11px;font-weight:700;letter-spacing:0.03em;">R</span>'
    elif party:
        return f'<span style="display:inline-block;background:#6b7280;color:#fff;padding:1px 7px;border-radius:3px;font-size:11px;font-weight:700;letter-spacing:0.03em;">{party}</span>'
    return ""


def _locality_footer_html() -> str:
    """Subtle Locality AI footer mark."""
    return '''<tr><td style="padding:12px 32px 16px 32px;text-align:center;">
  <div style="font-size:9px;color:#b0b0b0;letter-spacing:0.18em;font-family:Syne,Inter,-apple-system,sans-serif;">LOCALITY <span style="font-weight:400;">AI</span></div>
</td></tr>'''


def _district_competitor_count(district: str, all_tracked: dict, exclude_name: str = "") -> int:
    """Count how many other candidates have filed for the same district."""
    count = 0
    for v in all_tracked.values():
        if format_district(v.get("office", "")) == district:
            if v.get("candidate_name", "") != exclude_name:
                count += 1
    return count


def _days_since_filing(filed_date: str) -> str:
    """Return human-readable time since filing, e.g. '3d', '2w', '3mo'."""
    if not filed_date:
        return ""
    try:
        dt = datetime.strptime(filed_date, "%Y-%m-%d")
        delta = datetime.now() - dt
        days = delta.days
        if days < 0:
            return "today"
        if days == 0:
            return "today"
        if days == 1:
            return "1d"
        if days < 14:
            return f"{days}d"
        if days < 60:
            return f"{days // 7}w"
        return f"{days // 30}mo"
    except ValueError:
        return ""


def _load_vrems_party_lookup(all_tracked: dict) -> dict:
    """
    Load party data from VREMS cross-reference file (party_lookup.json).

    Matches ethics monitor candidates to VREMS party data by district + last name.
    Returns party_results dict in existing format: {"Candidate, Name": {"party": "R", ...}}
    """
    lookup_file = Path(__file__).parent / "party_lookup.json"
    if not lookup_file.exists():
        log("party_lookup.json not found — skipping VREMS party enrichment")
        return {}

    try:
        with open(lookup_file) as f:
            lookup = json.load(f)
    except Exception as e:
        log(f"Error loading party_lookup.json: {e}")
        return {}

    party_map = {"Republican": "R", "Democratic": "D", "Libertarian": "L", "United Citizens": "UC"}
    results = {}

    for v in all_tracked.values():
        cand_name = v.get("candidate_name", "")
        if not cand_name:
            continue

        district = format_district(v.get("office", ""))
        if not district:
            continue

        # Extract last name from "Last, First M" format
        last_name = cand_name.split(",")[0].strip() if "," in cand_name else cand_name.strip().split()[-1]

        district_data = lookup.get(district, {})
        # Case-insensitive last name match
        for vrems_name, party_full in district_data.items():
            if vrems_name.lower() == last_name.lower():
                abbrev = party_map.get(party_full, party_full)
                results[cand_name] = {"party": abbrev, "confidence": "HIGH", "source": "vrems"}
                break

    log(f"VREMS party enrichment: {len(results)}/{len(all_tracked)} candidates matched")
    return results


def build_email_template_a(
    new_reports: list[dict],
    all_tracked: dict,
    party_results: dict,
) -> tuple[str, str]:
    """
    Template A: 'Daily Brief' — Filed Today headline table + all tracked.
    Locality AI branding (teal palette, Syne font). 720px wide.

    Returns (text_content, html_content).
    """
    today_str = datetime.now().strftime("%B %d, %Y")
    party_results = party_results or {}

    # Build district-to-candidates map for competitor counts
    district_candidates = {}
    for v in all_tracked.values():
        d = format_district(v.get("office", ""))
        if d:
            district_candidates.setdefault(d, []).append(v)

    # Sort all tracked by date descending
    sorted_tracked = sorted(
        [{"report_id": k, **v} for k, v in all_tracked.items()],
        key=lambda x: x.get("filed_date", ""),
        reverse=True,
    )

    # Dem coverage stats — count total Dem candidates and unique districts
    dem_candidates_count = 0
    dem_districts = set()
    for v in all_tracked.values():
        d = format_district(v.get("office", ""))
        cand_name = v.get("candidate_name", "")
        party = (party_results.get(cand_name, {}).get("party", "") or "").upper()
        if d and party in ("D", "DEM", "DEMOCRAT", "DEMOCRATIC"):
            dem_candidates_count += 1
            dem_districts.add(d)
    dem_districts_filed = len(dem_districts)
    dem_coverage_pct = round(dem_districts_filed / 124 * 100) if dem_districts_filed else 0
    gap_districts = 124 - dem_districts_filed

    # New Dem candidates today: count Dem candidates in today's new_reports
    new_dem_today = sum(
        1 for r in new_reports
        if (party_results.get(r.get("candidate_name", ""), {}).get("party", "") or "").upper()
        in ("D", "DEM", "DEMOCRAT", "DEMOCRATIC")
    )

    total_tracked = len(all_tracked)

    # === PLAIN TEXT ===
    text = f"SC House Candidate Filings Report\n{today_str}\n"
    text += "=" * 60 + "\n\n"
    text += f"Dem Filed: {dem_candidates_count} ({dem_coverage_pct}% coverage)  |  Gaps: {gap_districts}  |  New Dem Today: {new_dem_today}\n"
    text += f"\nInteractive Map: https://russellteter.github.io/sc-filing-coverage-map/sc\n"
    text += f"Master Tracker: https://docs.google.com/spreadsheets/d/1_SztBdJyl4FoPrtPiduKvrrnttisZDAJRLiHeoyFxLY/edit?gid=77275834#gid=77275834\n\n"

    text += f"FILED TODAY ({len(new_reports)})\n" + "-" * 60 + "\n"
    if new_reports:
        text += f"{'Name':<24} {'District':<12} {'Party':<6} {'Filed':<12} {'In Dist'}\n"
        text += "-" * 66 + "\n"
        for r in new_reports:
            name = format_candidate_name(r["candidate_name"])
            district = format_district(r.get("office", ""))
            party = party_results.get(r["candidate_name"], {}).get("party", "") or "-"
            filed = r.get("last_updated", "N/A")
            competitors = _district_competitor_count(district, all_tracked, r["candidate_name"])
            comp_str = f"{competitors + 1}" if competitors > 0 else "1"
            text += f"  {name:<22} {district:<12} {party:<6} {filed:<12} {comp_str}\n"
            text += f"  {r['url']}\n"
    else:
        text += "  No new filings today.\n"
    text += "\n"

    text += f"ALL TRACKED CANDIDATES ({total_tracked})\n" + "-" * 60 + "\n"
    text += f"{'Filed':<10} {'Name':<24} {'District':<12} {'Party':<6} {'Cycle':<6} {'Age'}\n"
    text += "-" * 66 + "\n"
    for r in sorted_tracked:
        name = format_candidate_name(r["candidate_name"])
        district = format_district(r.get("office", ""))
        date_d = format_date_compact(r.get("filed_date", ""))
        party = party_results.get(r["candidate_name"], {}).get("party", "") or r.get("party", "") or "-"
        cycle = r.get("election_year", "")
        age = _days_since_filing(r.get("filed_date", ""))
        text += f"  {date_d:<8} {name:<24} {district:<12} {party:<6} {cycle:<6} {age}\n"

    text += f"\n{'=' * 60}\nSC House Candidate Tracker · 124 districts\n"

    # === HTML ===
    # Locality AI palette
    #   Primary Teal: #1ED4C2   Secondary Teal: #5CD4C8
    #   Deep Teal: #1A4A45      Medium Teal: #1CCAB8
    #   Dark BG: #1F1F23        Light BG: #F8F8F8
    new_count = len(new_reports)
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&display=swap" rel="stylesheet">
</head>
<body style="margin:0;padding:0;background-color:#F8F8F8;font-family:Syne,Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#F8F8F8;padding:20px 0;">
<tr><td align="center">
<table width="720" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;">

<!-- HEADER -->
<tr><td style="background:#1F1F23;padding:28px 36px 24px 36px;">
  <table width="100%" cellpadding="0" cellspacing="0"><tr>
    <td>
      <div style="width:48px;height:3px;background:#1ED4C2;border-radius:2px;margin-bottom:16px;"></div>
      <div style="color:#ffffff;font-size:22px;font-weight:700;font-family:Syne,Inter,sans-serif;letter-spacing:0.02em;margin-bottom:6px;">SC House Candidate Filings Report</div>
      <div style="color:rgba(255,255,255,0.55);font-size:13px;letter-spacing:0.05em;">{today_str}</div>
    </td>
  </tr></table>
</td></tr>

<!-- TEAL ACCENT LINE -->
<tr><td style="height:3px;background:linear-gradient(90deg,#1ED4C2,#5CD4C8);"></td></tr>

<!-- QUICK LINKS -->
<tr><td style="padding:12px 36px 0 36px;text-align:center;">
  <a href="https://russellteter.github.io/sc-filing-coverage-map/sc" style="display:inline-block;background:#1CCAB8;color:#ffffff;font-size:13px;font-weight:600;padding:10px 24px;border-radius:4px;text-decoration:none;letter-spacing:0.02em;">View Interactive Coverage Map</a>
  &nbsp;&nbsp;
  <a href="https://docs.google.com/spreadsheets/d/1_SztBdJyl4FoPrtPiduKvrrnttisZDAJRLiHeoyFxLY/edit?gid=77275834#gid=77275834" style="display:inline-block;background:#1A4A45;color:#ffffff;font-size:13px;font-weight:600;padding:10px 24px;border-radius:4px;text-decoration:none;letter-spacing:0.02em;">View Master Candidate Tracker</a>
</td></tr>

<!-- DEM COVERAGE STATS -->
<tr><td style="padding:12px 36px 8px 36px;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#F0FDFA;border-radius:6px;border:1px solid #D1FAE5;">
    <tr>
      <td align="center" style="padding:10px 8px;">
        <div style="font-size:20px;font-weight:800;color:#1A4A45;">{dem_candidates_count}</div>
        <div style="font-size:9px;color:#1A4A45;text-transform:uppercase;letter-spacing:0.1em;opacity:0.7;">Dem Filed</div>
      </td>
      <td align="center" style="padding:10px 8px;">
        <div style="font-size:20px;font-weight:800;color:#1A4A45;">{dem_coverage_pct}%</div>
        <div style="font-size:9px;color:#1A4A45;text-transform:uppercase;letter-spacing:0.1em;opacity:0.7;">Coverage</div>
      </td>
      <td align="center" style="padding:10px 8px;">
        <div style="font-size:20px;font-weight:800;color:#EA580C;">{gap_districts}</div>
        <div style="font-size:9px;color:#1A4A45;text-transform:uppercase;letter-spacing:0.1em;opacity:0.7;">Gaps</div>
      </td>
      <td align="center" style="padding:10px 8px;">
        <div style="font-size:20px;font-weight:800;color:#16A34A;">{new_dem_today}</div>
        <div style="font-size:9px;color:#1A4A45;text-transform:uppercase;letter-spacing:0.1em;opacity:0.7;">New Today</div>
      </td>
    </tr>
  </table>
</td></tr>

<!-- FILED TODAY -->
<tr><td style="padding:24px 36px 8px 36px;">
  <table width="100%" cellpadding="0" cellspacing="0"><tr>
    <td style="font-size:16px;font-weight:700;color:#1A4A45;letter-spacing:0.15em;text-transform:uppercase;">Filed Today</td>
    <td align="right">"""

    if new_reports:
        html += f'<span style="display:inline-block;background:#1ED4C2;color:#1F1F23;padding:3px 12px;border-radius:12px;font-size:13px;font-weight:700;">{new_count}</span>'

    html += """</td></tr></table>
  <div style="height:1px;background:#e0e0e0;margin-top:12px;"></div>
</td></tr>

<tr><td style="padding:8px 36px 20px 36px;">"""

    if new_reports:
        # Filed Today table with expanded columns
        html += """
  <table width="100%" cellpadding="0" cellspacing="0" style="font-size:13px;margin-top:4px;">
    <thead><tr>
      <th style="text-align:left;padding:8px 6px;background:#1A4A45;color:#fff;font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:0.08em;border-radius:4px 0 0 0;">Candidate</th>
      <th style="text-align:left;padding:8px 6px;background:#1A4A45;color:#fff;font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:0.08em;">District</th>
      <th style="text-align:center;padding:8px 6px;background:#1A4A45;color:#fff;font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:0.08em;">Party</th>
      <th style="text-align:left;padding:8px 6px;background:#1A4A45;color:#fff;font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:0.08em;">Filed</th>
      <th style="text-align:center;padding:8px 6px;background:#1A4A45;color:#fff;font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:0.08em;">In Dist</th>
      <th style="text-align:center;padding:8px 6px;background:#1A4A45;color:#fff;font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:0.08em;border-radius:0 4px 0 0;"></th>
    </tr></thead><tbody>"""

        for r in new_reports:
            name = format_candidate_name(r["candidate_name"])
            district = format_district(r.get("office", ""))
            filed = r.get("last_updated", "N/A")
            party = party_results.get(r["candidate_name"], {}).get("party", "")
            badge = _party_badge_html(party) if party else '<span style="color:#b0b0b0;font-size:11px;">&mdash;</span>'
            url = r.get("url", "#")
            competitors = _district_competitor_count(district, all_tracked, r["candidate_name"])
            in_dist = competitors + 1  # including this candidate
            in_dist_color = "#dc2626" if in_dist > 1 else "#888"

            html += f"""
    <tr>
      <td style="padding:8px 6px;border-bottom:1px solid #eee;font-weight:600;color:#1F1F23;font-size:13px;">{name}</td>
      <td style="padding:8px 6px;border-bottom:1px solid #eee;color:#1A4A45;font-size:12px;">{district}</td>
      <td style="padding:8px 6px;border-bottom:1px solid #eee;text-align:center;">{badge}</td>
      <td style="padding:8px 6px;border-bottom:1px solid #eee;color:#888;font-size:12px;">{filed}</td>
      <td style="padding:8px 6px;border-bottom:1px solid #eee;text-align:center;font-weight:700;color:{in_dist_color};font-size:12px;">{in_dist}</td>
      <td style="padding:8px 6px;border-bottom:1px solid #eee;text-align:center;"><a href="{url}" style="color:#1CCAB8;text-decoration:none;font-size:12px;font-weight:600;">View &rarr;</a></td>
    </tr>"""

        html += "</tbody></table>"
    else:
        html += '<p style="color:#888;font-style:italic;font-size:14px;margin:12px 0;">No new filings today.</p>'

    html += """</td></tr>

<!-- ALL TRACKED -->
<tr><td style="padding:16px 36px 8px 36px;">
  <table width="100%" cellpadding="0" cellspacing="0"><tr>
    <td style="font-size:14px;font-weight:700;color:#1A4A45;letter-spacing:0.15em;text-transform:uppercase;">All Tracked Candidates</td>
    <td align="right" style="font-size:11px;color:#b0b0b0;">"""
    html += f'{total_tracked} candidates'
    html += """</td></tr></table>
  <div style="height:1px;background:#e0e0e0;margin-top:10px;"></div>
</td></tr>
<tr><td style="padding:4px 36px 24px 36px;">
  <table width="100%" cellpadding="0" cellspacing="0" style="font-size:12px;">
    <thead><tr>
      <th style="text-align:left;padding:6px 5px;background:#F8F8F8;color:#1A4A45;font-weight:600;font-size:9px;text-transform:uppercase;letter-spacing:0.08em;">Filed</th>
      <th style="text-align:left;padding:6px 5px;background:#F8F8F8;color:#1A4A45;font-weight:600;font-size:9px;text-transform:uppercase;letter-spacing:0.08em;">Candidate</th>
      <th style="text-align:left;padding:6px 5px;background:#F8F8F8;color:#1A4A45;font-weight:600;font-size:9px;text-transform:uppercase;letter-spacing:0.08em;">District</th>
      <th style="text-align:center;padding:6px 5px;background:#F8F8F8;color:#1A4A45;font-weight:600;font-size:9px;text-transform:uppercase;letter-spacing:0.08em;">Party</th>
      <th style="text-align:center;padding:6px 5px;background:#F8F8F8;color:#1A4A45;font-weight:600;font-size:9px;text-transform:uppercase;letter-spacing:0.08em;">Cycle</th>
      <th style="text-align:center;padding:6px 5px;background:#F8F8F8;color:#1A4A45;font-weight:600;font-size:9px;text-transform:uppercase;letter-spacing:0.08em;">In Dist</th>
      <th style="text-align:center;padding:6px 5px;background:#F8F8F8;color:#1A4A45;font-weight:600;font-size:9px;text-transform:uppercase;letter-spacing:0.08em;">Age</th>
    </tr></thead><tbody>"""

    for r in sorted_tracked:
        date_d = format_date_compact(r.get("filed_date", ""))
        name = format_candidate_name(r["candidate_name"])
        district = format_district(r.get("office", ""))
        url = r.get("url", "#")
        party = party_results.get(r["candidate_name"], {}).get("party", "") or r.get("party", "")
        badge = _party_badge_html(party) if party else '<span style="color:#ccc;">&mdash;</span>'
        cycle = r.get("election_year", "")
        age = _days_since_filing(r.get("filed_date", ""))
        competitors = _district_competitor_count(district, all_tracked, r["candidate_name"])
        in_dist = competitors + 1
        in_dist_color = "#dc2626" if in_dist > 1 else "#ccc"

        html += f"""
    <tr>
      <td style="padding:5px 5px;border-bottom:1px solid #f0f0f0;color:#888;font-size:11px;">{date_d}</td>
      <td style="padding:5px 5px;border-bottom:1px solid #f0f0f0;"><a href="{url}" style="color:#1A4A45;text-decoration:none;font-weight:500;font-size:12px;">{name}</a></td>
      <td style="padding:5px 5px;border-bottom:1px solid #f0f0f0;color:#1A4A45;font-size:11px;">{district}</td>
      <td style="padding:5px 5px;border-bottom:1px solid #f0f0f0;text-align:center;">{badge}</td>
      <td style="padding:5px 5px;border-bottom:1px solid #f0f0f0;text-align:center;color:#888;font-size:10px;">{cycle}</td>
      <td style="padding:5px 5px;border-bottom:1px solid #f0f0f0;text-align:center;font-weight:600;color:{in_dist_color};font-size:11px;">{in_dist}</td>
      <td style="padding:5px 5px;border-bottom:1px solid #f0f0f0;text-align:center;color:#b0b0b0;font-size:10px;">{age}</td>
    </tr>"""

    html += """
    </tbody></table>
</td></tr>

<!-- SHEET BUTTON -->
<tr><td style="padding:16px 36px;text-align:center;">
  <a href="https://docs.google.com/spreadsheets/d/1_SztBdJyl4FoPrtPiduKvrrnttisZDAJRLiHeoyFxLY/edit?gid=77275834#gid=77275834" style="display:inline-block;background:#1A4A45;color:#ffffff;font-size:13px;font-weight:600;padding:10px 24px;border-radius:4px;text-decoration:none;letter-spacing:0.02em;">View Master Candidate Tracker</a>
</td></tr>

<!-- FOOTER -->
<tr><td style="padding:20px 36px 8px 36px;text-align:center;border-top:1px solid #e0e0e0;">
  <div style="font-size:12px;font-weight:600;color:#1A4A45;">SC House Candidate Tracker</div>
  <div style="font-size:10px;color:#b0b0b0;margin-top:4px;">Monitoring Initial Report filings across 124 House districts</div>
</td></tr>
"""
    html += _locality_footer_html()
    html += """
</table>
</td></tr></table>
</body></html>"""

    return text, html


def build_email_template_b(
    new_reports: list[dict],
    all_tracked: dict,
    party_results: dict,
) -> tuple[str, str]:
    """
    Template B: 'Intelligence Digest' — Filed Today table + stats + district-sorted list.
    Locality AI branding (teal palette, Syne font).

    Returns (text_content, html_content).
    """
    today_str = datetime.now().strftime("%B %d, %Y")
    party_results = party_results or {}

    new_count = len(new_reports)
    total_tracked = len(all_tracked)
    districts_active = len(set(
        format_district(v.get("office", ""))
        for v in all_tracked.values()
        if format_district(v.get("office", ""))
    ))

    # Sort by district number
    sorted_by_district = sorted(
        [{"report_id": k, **v} for k, v in all_tracked.items()],
        key=lambda x: (
            int(re.search(r'(\d+)', format_district(x.get("office", "")) or "0").group(1))
            if re.search(r'(\d+)', format_district(x.get("office", "")) or "0")
            else 999
        ),
    )

    # District-to-candidates map
    district_candidates = {}
    for r in sorted_by_district:
        d = format_district(r.get("office", ""))
        if d:
            district_candidates.setdefault(d, []).append(r)

    # === PLAIN TEXT ===
    text = f"SC House Filing Intelligence\n{today_str}\n"
    text += "=" * 50 + "\n\n"
    text += f"Filed Today: {new_count}  |  Total Tracked: {total_tracked}  |  Districts: {districts_active}\n\n"

    text += "FILED TODAY\n" + "-" * 40 + "\n"
    if new_reports:
        text += f"{'Name':<24} {'District':<14} {'Party':<6} {'Filed'}\n"
        text += "-" * 56 + "\n"
        for r in new_reports:
            name = format_candidate_name(r["candidate_name"])
            district = format_district(r.get("office", ""))
            party = party_results.get(r["candidate_name"], {}).get("party", "") or "-"
            filed = r.get("last_updated", "N/A")
            text += f"  {name:<22} {district:<14} {party:<6} {filed}\n"
    else:
        text += "  No new filings today.\n"
    text += "\n"

    text += "ALL TRACKED (by district)\n" + "-" * 40 + "\n"
    for r in sorted_by_district:
        district = format_district(r.get("office", ""))
        name = format_candidate_name(r["candidate_name"])
        date_d = format_date_compact(r.get("filed_date", ""))
        text += f"  {district:<14} {name:<22} {date_d}\n"

    text += "\n" + "=" * 50 + "\n"
    text += "SC House Candidate Tracker · 124 districts\n"

    # === HTML ===
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&display=swap" rel="stylesheet">
</head>
<body style="margin:0;padding:0;background-color:#F8F8F8;font-family:Syne,Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#F8F8F8;padding:20px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;">

<!-- HEADER -->
<tr><td style="background:#1F1F23;padding:28px 32px 24px 32px;">
  <div style="color:#ffffff;font-size:19px;font-weight:700;font-family:Syne,Inter,sans-serif;text-transform:uppercase;letter-spacing:0.15em;margin-bottom:8px;">SC House Filing Intelligence</div>
  <div style="width:48px;height:3px;background:#1ED4C2;border-radius:2px;margin-bottom:10px;"></div>
  <div style="color:rgba(255,255,255,0.55);font-size:13px;letter-spacing:0.05em;">{today_str}</div>
</td></tr>

<!-- TEAL ACCENT LINE -->
<tr><td style="height:3px;background:linear-gradient(90deg,#1ED4C2,#5CD4C8);"></td></tr>

<!-- STATS BANNER -->
<tr><td style="padding:20px 32px;">
  <table width="100%" cellpadding="0" cellspacing="0">
  <tr>
    <td width="32%" align="center" style="padding:12px 6px;border:1px solid #e0e0e0;border-radius:6px;">
      <div style="font-size:26px;font-weight:800;color:#1A4A45;">{new_count}</div>
      <div style="font-size:10px;color:#1CCAB8;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;margin-top:2px;">Filed Today</div>
    </td>
    <td width="2%"></td>
    <td width="32%" align="center" style="padding:12px 6px;border:1px solid #e0e0e0;border-radius:6px;">
      <div style="font-size:26px;font-weight:800;color:#1A4A45;">{total_tracked}</div>
      <div style="font-size:10px;color:#1CCAB8;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;margin-top:2px;">Total Tracked</div>
    </td>
    <td width="2%"></td>
    <td width="32%" align="center" style="padding:12px 6px;border:1px solid #e0e0e0;border-radius:6px;">
      <div style="font-size:26px;font-weight:800;color:#1A4A45;">{districts_active}</div>
      <div style="font-size:10px;color:#1CCAB8;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;margin-top:2px;">Districts</div>
    </td>
  </tr></table>
</td></tr>

<!-- FILED TODAY TABLE -->
<tr><td style="padding:0 32px 8px 32px;">
  <div style="font-size:16px;font-weight:700;color:#1A4A45;letter-spacing:0.15em;text-transform:uppercase;">Filed Today</div>
  <div style="height:1px;background:#e0e0e0;margin-top:10px;"></div>
</td></tr>
<tr><td style="padding:8px 32px 20px 32px;">"""

    if new_reports:
        html += """
  <table width="100%" cellpadding="0" cellspacing="0" style="font-size:13px;margin-top:4px;">
    <thead><tr>
      <th style="text-align:left;padding:8px 6px;background:#1A4A45;color:#fff;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:0.1em;border-radius:4px 0 0 0;">Candidate</th>
      <th style="text-align:left;padding:8px 6px;background:#1A4A45;color:#fff;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:0.1em;">District</th>
      <th style="text-align:center;padding:8px 6px;background:#1A4A45;color:#fff;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:0.1em;">Party</th>
      <th style="text-align:left;padding:8px 6px;background:#1A4A45;color:#fff;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:0.1em;">Filed</th>
      <th style="text-align:center;padding:8px 6px;background:#1A4A45;color:#fff;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:0.1em;border-radius:0 4px 0 0;"></th>
    </tr></thead><tbody>"""

        for r in new_reports:
            name = format_candidate_name(r["candidate_name"])
            district = format_district(r.get("office", ""))
            filed = r.get("last_updated", "N/A")
            party = party_results.get(r["candidate_name"], {}).get("party", "")
            badge = _party_badge_html(party) if party else '<span style="color:#b0b0b0;font-size:11px;">&mdash;</span>'
            url = r.get("url", "#")

            # "Also in district" note
            others = [c for c in district_candidates.get(district, []) if c["candidate_name"] != r["candidate_name"]]
            also_note = ""
            if others:
                other_names = ", ".join(format_candidate_name(o["candidate_name"]) for o in others[:3])
                also_note = f'<div style="font-size:10px;color:#999;margin-top:2px;">Also in {district}: {other_names}</div>'

            html += f"""
    <tr>
      <td style="padding:8px 6px;border-bottom:1px solid #eee;font-weight:600;color:#1F1F23;font-size:13px;">{name}{also_note}</td>
      <td style="padding:8px 6px;border-bottom:1px solid #eee;color:#1A4A45;font-size:12px;">{district}</td>
      <td style="padding:8px 6px;border-bottom:1px solid #eee;text-align:center;">{badge}</td>
      <td style="padding:8px 6px;border-bottom:1px solid #eee;color:#888;font-size:12px;">{filed}</td>
      <td style="padding:8px 6px;border-bottom:1px solid #eee;text-align:center;"><a href="{url}" style="color:#1CCAB8;text-decoration:none;font-size:12px;font-weight:600;">View &rarr;</a></td>
    </tr>"""

        html += "</tbody></table>"
    else:
        html += '<p style="color:#888;font-style:italic;font-size:14px;margin:12px 0;">No new filings today.</p>'

    # All tracked (district-sorted)
    html += """</td></tr>

<tr><td style="padding:16px 32px 8px 32px;">
  <table width="100%" cellpadding="0" cellspacing="0"><tr>
    <td style="font-size:14px;font-weight:700;color:#1A4A45;letter-spacing:0.15em;text-transform:uppercase;">All Tracked Candidates</td>
    <td align="right" style="font-size:10px;color:#b0b0b0;letter-spacing:0.1em;">BY DISTRICT</td>
  </tr></table>
  <div style="height:1px;background:#e0e0e0;margin-top:10px;"></div>
</td></tr>
<tr><td style="padding:4px 32px 24px 32px;">
  <table width="100%" cellpadding="0" cellspacing="0" style="font-size:12px;">
    <thead><tr>
      <th style="text-align:left;padding:6px 6px;background:#F8F8F8;color:#1A4A45;font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;">Dist</th>
      <th style="text-align:left;padding:6px 6px;background:#F8F8F8;color:#1A4A45;font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;">Candidate</th>
      <th style="text-align:center;padding:6px 6px;background:#F8F8F8;color:#1A4A45;font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;">Party</th>
      <th style="text-align:left;padding:6px 6px;background:#F8F8F8;color:#1A4A45;font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;">Filed</th>
    </tr></thead><tbody>"""

    for r in sorted_by_district:
        district = format_district(r.get("office", ""))
        dist_num = re.search(r'(\d+)', district or "")
        dist_display = dist_num.group(1) if dist_num else district
        name = format_candidate_name(r["candidate_name"])
        date_d = format_date_compact(r.get("filed_date", ""))
        url = r.get("url", "#")
        party = party_results.get(r["candidate_name"], {}).get("party", "")
        badge = _party_badge_html(party) if party else '<span style="color:#ccc;">&mdash;</span>'

        html += f"""
    <tr>
      <td style="padding:5px 6px;border-bottom:1px solid #f0f0f0;color:#1A4A45;font-weight:600;font-size:12px;">{dist_display}</td>
      <td style="padding:5px 6px;border-bottom:1px solid #f0f0f0;"><a href="{url}" style="color:#1A4A45;text-decoration:none;font-weight:500;font-size:12px;">{name}</a></td>
      <td style="padding:5px 6px;border-bottom:1px solid #f0f0f0;text-align:center;">{badge}</td>
      <td style="padding:5px 6px;border-bottom:1px solid #f0f0f0;color:#888;font-size:11px;">{date_d}</td>
    </tr>"""

    html += """
    </tbody></table>
</td></tr>

<!-- FOOTER -->
<tr><td style="padding:20px 32px 8px 32px;text-align:center;border-top:1px solid #e0e0e0;">
  <div style="font-size:12px;font-weight:600;color:#1A4A45;">SC House Candidate Tracker</div>
  <div style="font-size:10px;color:#b0b0b0;margin-top:4px;">Monitoring Initial Report filings across 124 House districts</div>
</td></tr>
"""
    html += _locality_footer_html()
    html += """
</table>
</td></tr></table>
</body></html>"""

    return text, html


def log(message: str, level: str = "INFO") -> None:
    """Print structured log message."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{timestamp}] [{level}] {message}")


def get_statistics() -> dict:
    """Fetch current activity statistics from the API."""
    try:
        response = requests.get(STATISTICS_API, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log(f" Could not fetch statistics: {e}")
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

    # Navigate with retry logic (2 retries, 5s delay)
    for attempt in range(3):
        try:
            log(f"Navigating to {CAMPAIGN_REPORTS_URL}" + (f" (attempt {attempt + 1})" if attempt > 0 else ""))
            page.goto(CAMPAIGN_REPORTS_URL, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=30000)
            break
        except Exception as e:
            if attempt < 2:
                log(f"Navigation failed, retrying in 5s: {e}", "WARN")
                time.sleep(5)
            else:
                log(f"Navigation failed after 3 attempts: {e}", "ERROR")
                raise

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
        log(f" Could not set year filter: {e}")

    # Select "Initial" report type to find new candidates
    log("Setting report type filter to 'Initial'")
    try:
        report_type_dropdown = page.get_by_title("Report Name dropdown").get_by_role("listbox")
        report_type_dropdown.click()
        page.wait_for_timeout(500)
        page.get_by_role("option", name="Initial").click()
        page.wait_for_timeout(500)
    except Exception as e:
        log(f" Could not set report type filter: {e}")

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
        log(f" Could not sort by Last Updated: {e}")

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
                log(f" Error extracting row {i}: {e}")
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

    if len(reports) == 0:
        log("Scraper returned 0 results — site may have no Initial Reports for this period", "WARN")
    else:
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

    # Filter to: House AND filed in calendar year 2025
    historical = {}
    excluded_wrong_date = 0
    excluded_wrong_office = 0

    for r in unique_reports:
        # Must be House
        if not is_state_house(r.get("office", "")):
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

    log(f"  Filtered: {excluded_wrong_office} non-House, {excluded_wrong_date} not filed in 2025")
    log(f"  Result: {len(historical)} House Initial Reports filed in 2025")
    return historical


def load_state() -> dict:
    """Load previous state from JSON file with validation and backward compatibility."""
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

        # Validate expected types
        if not isinstance(state, dict):
            log("State file is not a dict, resetting", "WARN")
            return default_state

        # Ensure seen_report_ids is a list
        if not isinstance(state.get("seen_report_ids"), list):
            log("seen_report_ids invalid, resetting to empty list", "WARN")
            state["seen_report_ids"] = []

        # Ensure required fields exist (backward compatibility)
        if not isinstance(state.get("reports_with_metadata"), dict):
            state["reports_with_metadata"] = {}
        if not isinstance(state.get("historical_2025"), dict):
            state["historical_2025"] = {"cached_date": None, "reports": {}}
        if "reports" not in state["historical_2025"]:
            state["historical_2025"]["reports"] = {}

        return state
    except (json.JSONDecodeError, ValueError) as e:
        log(f"State file corrupted, resetting: {e}", "WARN")
        return default_state
    except Exception as e:
        log(f"Could not load state file: {e}", "ERROR")
        return default_state


def save_state(state: dict) -> None:
    """Save state to JSON file."""
    state["last_checked"] = datetime.utcnow().isoformat() + "Z"

    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
        log(f"State saved with {len(state.get('seen_report_ids', []))} tracked reports")
    except Exception as e:
        log(f"Error saving state: {e}", "ERROR")


def find_new_reports(reports: list[dict], state: dict) -> list[dict]:
    """Find Initial Reports for House that haven't been seen before."""
    seen_ids = set(state.get("seen_report_ids", []))

    new_reports = []
    filtered_out = 0

    for r in reports:
        if r["report_id"] in seen_ids:
            continue

        # Filter to only SC House candidates
        if not is_state_house(r.get("office", "")):
            filtered_out += 1
            continue

        new_reports.append(r)

    if filtered_out > 0:
        log(f"Filtered out {filtered_out} non-House reports")

    return new_reports


def send_daily_digest(
    new_reports: list[dict],
    last_30_days: list[dict],
    historical_2025: dict,
    total_tracked: int,
    party_results: dict = None
) -> bool:
    """
    Send daily digest email using the configured branded template.

    Uses EMAIL_TEMPLATE env var to select template:
    - "A" = Daily Brief (default)
    - "B" = Intelligence Digest
    """
    party_results = party_results or {}
    if not NOTIFICATION_EMAIL:
        log("Email not configured - NOTIFICATION_EMAIL not set")
        return False

    if not RESEND_API_KEY and not SENDGRID_API_KEY:
        log("Email not configured - set RESEND_API_KEY or SENDGRID_API_KEY")
        return False

    subject = get_subject_line(len(new_reports))

    # Merge all tracked data for template use
    all_tracked = {}
    all_tracked.update(historical_2025)
    for rid, meta in (last_30_days if isinstance(last_30_days, dict) else {}).items():
        all_tracked.setdefault(rid, meta)
    # Also merge reports_with_metadata style list
    if isinstance(last_30_days, list):
        for r in last_30_days:
            rid = r.get("report_id", "")
            if rid and rid not in all_tracked:
                all_tracked[rid] = r

    log(f"Using email template: {EMAIL_TEMPLATE}")
    if EMAIL_TEMPLATE.upper() == "B":
        text_content, html_content = build_email_template_b(new_reports, all_tracked, party_results)
    else:
        text_content, html_content = build_email_template_a(new_reports, all_tracked, party_results)

    if RESEND_API_KEY:
        return _send_via_resend(subject, text_content, html_content)
    else:
        return _send_via_sendgrid(subject, text_content, html_content)


def _send_via_resend(subject: str, text_content: str, html_content: str) -> bool:
    """Send email via Resend API."""
    # Support comma-separated emails in NOTIFICATION_EMAIL
    recipients = [email.strip() for email in NOTIFICATION_EMAIL.split(",") if email.strip()]

    if not recipients:
        log("No valid recipient emails found")
        return False

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "from": FROM_EMAIL,
                "to": recipients,
                "subject": subject,
                "text": text_content,
                "html": html_content
            },
            timeout=30
        )

        if response.status_code in [200, 201]:
            log(f"Email sent successfully via Resend to {', '.join(recipients)}")
            return True
        else:
            log(f"Resend failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        log(f"Error sending via Resend: {e}")
        return False


def _send_via_sendgrid(subject: str, text_content: str, html_content: str) -> bool:
    """Send email via SendGrid API."""
    # Support comma-separated emails in NOTIFICATION_EMAIL
    recipients = [{"email": email.strip()} for email in NOTIFICATION_EMAIL.split(",") if email.strip()]

    if not recipients:
        log("No valid recipient emails found")
        return False

    try:
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {SENDGRID_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "personalizations": [{"to": recipients}],
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
            recipient_list = ", ".join([r["email"] for r in recipients])
            log(f"Email sent successfully via SendGrid to {recipient_list}")
            return True
        else:
            log(f"SendGrid failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        log(f"Error sending via SendGrid: {e}")
        return False


def detect_parties_for_candidates(candidates: list[dict]) -> dict:
    """
    Detect party affiliations for a list of candidates.

    Args:
        candidates: List of candidate dicts with candidate_name, office, url

    Returns:
        Dict mapping candidate_name to PartyResult dict
    """
    if not PARTY_DETECTION_AVAILABLE:
        log("Party detection not available - skipping")
        return {}

    results = {}
    for candidate in candidates:
        name = candidate.get("candidate_name", "")
        office = candidate.get("office", "")

        if not name or not office:
            continue

        try:
            log(f"  Detecting party for: {name}")
            result = detect_party(name, office)

            if result:
                results[name] = {
                    "party": result.party,
                    "confidence": result.confidence,
                    "source": result.source,
                    "evidence_url": result.evidence_url,
                    "evidence_text": result.evidence_text
                }
                log(f"    -> {result.party} ({result.confidence}) via {result.source}")
            else:
                results[name] = {
                    "party": None,
                    "confidence": "UNKNOWN",
                    "source": None,
                    "evidence_url": None,
                    "evidence_text": None
                }
                log(f"    -> No party detected")

        except Exception as e:
            log(f"    -> Error detecting party: {e}")
            results[name] = {
                "party": None,
                "confidence": "UNKNOWN",
                "source": None,
                "evidence_url": None,
                "evidence_text": None
            }

    return results


def sync_to_google_sheets(
    new_reports: list[dict],
    party_results: dict,
    all_reports: dict
) -> bool:
    """
    Sync candidate data to Google Sheets.

    Args:
        new_reports: List of newly detected candidates
        party_results: Dict of party detection results
        all_reports: Full reports_with_metadata dict

    Returns:
        True if sync successful
    """
    if not SHEETS_SYNC_AVAILABLE:
        log("Google Sheets sync not available - skipping")
        return False

    try:
        sheets = SheetsSync()

        if not sheets.connect():
            log("Could not connect to Google Sheets")
            return False

        # Add new candidates
        added = 0
        for report in new_reports:
            name = report.get("candidate_name", "")
            office = report.get("office", "")
            report_id = report.get("report_id", "")

            # Get party info if available
            party_info = party_results.get(name, {})

            # Parse district and convert to SC-House format
            short_district = parse_district_from_office(office)  # Returns H091
            if short_district and short_district.startswith("H"):
                district_id = f"SC-House-{short_district[1:]}"
            else:
                district_id = short_district or ""

            result = sheets.add_candidate(
                report_id=report_id,
                candidate_name=name,
                district_id=district_id,
                filed_date=report.get("filed_date") or parse_date(report.get("last_updated", "")),
                ethics_report_url=report.get("url", ""),
                is_incumbent=False,
                detected_party=party_info.get("party", ""),
                detection_confidence=party_info.get("confidence", "UNKNOWN"),
                detection_source=party_info.get("source", ""),
                detection_evidence_url=party_info.get("evidence_url", ""),
            )

            if result.get("action") in ["added", "updated"]:
                added += 1
                log(f"  Added to sheets: {name} ({result['action']})")
            else:
                log(f"  Failed to add: {name} - {result.get('error', 'unknown')}")

        # Log sync result
        sheets.log_sync(
            event_type="DAILY_SYNC",
            details=f"Daily monitor sync - {len(new_reports)} new candidates",
            candidates_added=added,
            candidates_updated=0,
            party_detections=len([p for p in party_results.values() if p.get("party")]),
            errors=len(new_reports) - added,
        )
        log(f"Synced {added} candidates to Google Sheets")

        return True

    except Exception as e:
        log(f"Error syncing to Google Sheets: {e}")
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
    log("Tracking: SC House candidates filing Initial Reports")
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
        log(f"Error during scraping: {e}", "ERROR")
        sys.exit(1)

    log(f"Found {len(reports)} Initial Report(s) for current year")

    # Find new House Initial Reports
    new_reports = find_new_reports(reports, state)

    if new_reports:
        log(f"NEW: {len(new_reports)} SC House Initial Report(s)!")
        for report in new_reports:
            log(f"  - {report['candidate_name']} ({report['office']})")
    else:
        log("No new reports detected")

    # Detect party affiliations for new candidates (never blocks email)
    party_results = {}
    if new_reports and PARTY_DETECTION_AVAILABLE:
        try:
            log("Detecting party affiliations for new candidates...")
            party_results = detect_parties_for_candidates(new_reports)
            log(f"Party detection complete: {len(party_results)} candidates processed")
            parties_found = sum(1 for r in party_results.values() if r.get("party"))
            log(f"  Parties detected: {parties_found}/{len(party_results)}")
        except Exception as e:
            log(f"Party detection failed, continuing without it: {e}", "WARN")
            party_results = {}

    # Update state with report IDs and metadata
    all_report_ids = list(set(
        state.get("seen_report_ids", []) +
        [r["report_id"] for r in reports]
    ))
    state["seen_report_ids"] = all_report_ids

    # Store metadata for House reports (for 30-day history)
    reports_metadata = state.get("reports_with_metadata", {})
    for r in reports:
        if is_state_house(r.get("office", "")):
            candidate_name = r["candidate_name"]
            party_info = party_results.get(candidate_name, {})

            reports_metadata[r["report_id"]] = {
                "candidate_name": candidate_name,
                "office": r["office"],
                "election_year": r.get("election_year", ""),
                "report_name": r["report_name"],
                "filed_date": parse_date(r["last_updated"]),
                "url": r["url"],
                # Party detection results
                "party": party_info.get("party"),
                "party_confidence": party_info.get("confidence"),
                "party_source": party_info.get("source"),
                "party_evidence_url": party_info.get("evidence_url"),
            }
    state["reports_with_metadata"] = reports_metadata

    # Sync to Google Sheets
    if SHEETS_SYNC_AVAILABLE and new_reports:
        log("Syncing to Google Sheets...")
        sync_to_google_sheets(new_reports, party_results, reports_metadata)

    # Update 2025 cache
    state["historical_2025"] = {
        "cached_date": datetime.utcnow().isoformat() + "Z",
        "reports": historical_2025
    }

    # Calculate last 30 days from metadata
    last_30_days = get_last_30_days(reports_metadata)
    log(f"Last 30 days: {len(last_30_days)} House filings")
    log(f"2025 historical: {len(historical_2025)} House filings")

    # ALWAYS send daily digest (not conditional)
    log("Sending daily digest email...")
    send_daily_digest(
        new_reports=new_reports,
        last_30_days=last_30_days,
        historical_2025=historical_2025,
        total_tracked=len(reports_metadata),
        party_results=party_results
    )

    # Save state
    save_state(state)

    log("=" * 60)
    log("SC Ethics Initial Report Monitor - Complete")
    log("=" * 60)

    return len(new_reports)


def _load_vrems_candidates() -> tuple[dict, dict, list[dict]]:
    """
    Load all candidates from VREMS state.json — the production data source.

    Returns (all_tracked, party_results, new_today) where:
    - all_tracked: dict keyed by candidate_key with template-compatible fields
    - party_results: dict mapping candidate_name to party info
    - new_today: list of candidates filed today (for "Filed Today" section)
    """
    vrems_state_file = Path.home() / "Desktop" / "sc-vrems-filing-monitor" / "state.json"
    if not vrems_state_file.exists():
        log(f"VREMS state not found at {vrems_state_file}")
        return {}, {}, []

    with open(vrems_state_file) as f:
        vrems_state = json.load(f)

    metadata = vrems_state.get("candidates_metadata", {})
    log(f"Loaded {len(metadata)} candidates from VREMS state")

    party_map = {"Republican": "R", "Democratic": "D", "Libertarian": "L", "United Citizens": "UC"}
    all_tracked = {}
    party_results = {}
    new_today = []
    today_str = datetime.now().strftime("%Y-%m-%d")

    for key, info in metadata.items():
        full_name = info.get("full_name", "")
        if not full_name:
            continue

        # Convert "First M Last" → "Last, First M" for template compatibility
        parts = full_name.strip().split()
        if len(parts) >= 2:
            candidate_name = f"{parts[-1]}, {' '.join(parts[:-1])}"
        else:
            candidate_name = full_name

        district_num = info.get("district", "")
        office = info.get("office", "")
        # Normalize office to match template's format_district() expectations
        if district_num and "district" not in office.lower():
            office = f"SC House of Representatives District {int(district_num)}"

        filed_date = info.get("date_filed", "")

        tracked_entry = {
            "candidate_name": candidate_name,
            "office": office,
            "filed_date": filed_date,
            "election_year": "2026",
            "url": "",
        }
        all_tracked[key] = tracked_entry

        # Build party_results from VREMS party data
        party_full = info.get("party", "")
        if party_full:
            abbrev = party_map.get(party_full, party_full)
            party_results[candidate_name] = {"party": abbrev, "confidence": "HIGH", "source": "vrems"}

        # Check if filed today
        if filed_date == today_str:
            new_today.append({
                "report_id": key,
                "candidate_name": candidate_name,
                "office": office,
                "election_year": "2026",
                "last_updated": filed_date,
                "filed_date": filed_date,
                "url": "",
            })

    return all_tracked, party_results, new_today


def send_test_emails() -> bool:
    """
    Send test email using real VREMS data (the production data source).
    Shows today's new filings and all tracked candidates with party info.
    """
    log("=" * 60)
    log("SC House Monitor — TEST EMAIL MODE")
    log("Loading real data from VREMS state.json")
    log("=" * 60)

    if not NOTIFICATION_EMAIL:
        log("ERROR: NOTIFICATION_EMAIL not set")
        return False
    if not RESEND_API_KEY and not SENDGRID_API_KEY:
        log("ERROR: No email API key configured")
        return False

    # Load VREMS data — the real production source
    all_tracked, party_results, new_today = _load_vrems_candidates()
    log(f"Loaded {len(all_tracked)} candidates, {len(party_results)} with party data")
    log(f"Filed today: {len(new_today)}")

    # Send test email
    log("Building email with real VREMS data...")
    text, html = build_email_template_a(new_today, all_tracked, party_results)
    date_str = datetime.now().strftime("%-m/%-d")
    new_count = len(new_today)
    if new_count > 0:
        subject = f"[TEST] SC House Candidate Filings Report - {new_count} New Today - {date_str}"
    else:
        subject = f"[TEST] SC House Candidate Filings Report - No New Filings - {date_str}"
    if RESEND_API_KEY:
        result = _send_via_resend(subject, text, html)
    else:
        result = _send_via_sendgrid(subject, text, html)

    log("=" * 60)
    if result:
        log("Test email sent! Check inbox for visual review.")
    else:
        log("Test email FAILED — check API keys and logs above.")
    log("=" * 60)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SC House Initial Report Monitor")
    parser.add_argument(
        "--test-email",
        action="store_true",
        help="Send both email templates with mock data for visual review",
    )
    args = parser.parse_args()

    if args.test_email:
        sys.exit(0 if send_test_emails() else 1)
    else:
        sys.exit(0 if main() >= 0 else 1)

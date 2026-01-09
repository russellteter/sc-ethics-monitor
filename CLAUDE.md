# SC Ethics Initial Report Monitor - Project Context

## Quick Start for New Sessions

```bash
# This project monitors SC Ethics Commission for NEW CANDIDATE Initial Reports
# Target: SC House and Senate candidates only
# Purpose: Help party recruiters identify serious candidates early
# Repository: https://github.com/russellteter/sc-ethics-monitor
# Status: OPERATIONAL - Email notifications working via Resend
```

---

## Project Overview

| Attribute | Value |
|-----------|-------|
| **Purpose** | Detect new SC House & Senate candidates via Initial Report filings |
| **What's an Initial Report?** | First required filing when candidate raises/spends $500 |
| **Why it matters** | Earliest signal of serious candidate intent |
| **Primary Output** | Email alerts when new candidates file Initial Reports |
| **Scope** | SC House (124 districts) + SC Senate (46 districts) only |
| **Schedule** | Daily at 9:00 AM EST via GitHub Actions |
| **Cost** | $0/month (free tier services) |
| **Status** | Production-ready, operational |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DAILY WORKFLOW                           │
├─────────────────────────────────────────────────────────────┤
│  GitHub Actions (9 AM EST)                                  │
│         │                                                   │
│         ▼                                                   │
│  Python Script (src/monitor.py)                             │
│         │                                                   │
│         ▼                                                   │
│  Playwright Browser → SC Ethics Website                     │
│         │              (Filter: Report Type = "Initial")    │
│         ▼                                                   │
│  Extract Initial Reports                                    │
│         │                                                   │
│         ▼                                                   │
│  Filter to House/Senate only (post-scrape)                  │
│         │                                                   │
│         ▼                                                   │
│  Compare to state.json (seen report IDs)                    │
│         │                                                   │
│         ▼                                                   │
│  New candidates? ──Yes──► Send Email Alert (Resend API)     │
│         │                                                   │
│         ▼                                                   │
│  Update state.json → Commit to repo                         │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
sc-ethics-report-monitor/
├── CLAUDE.md                    # THIS FILE - Project context for Claude
├── README.md                    # User-facing setup instructions
├── requirements.txt             # Python dependencies (playwright, requests)
├── state.json                   # Tracked report IDs (auto-updated by workflow)
├── .github/
│   └── workflows/
│       └── monitor.yml          # GitHub Actions workflow definition
├── src/
│   └── monitor.py               # Main monitoring script (all logic here)
├── docs/
│   └── SC-Ethics-Monitor-Overview.md  # Stakeholder documentation
└── claudedocs/                  # Claude-specific documentation (if needed)
```

---

## Key Components

### 1. Main Script: `src/monitor.py`

**Core Functions:**
| Function | Purpose |
|----------|---------|
| `scrape_recent_reports()` | Navigate website with "Initial" report filter, extract filing data |
| `is_house_or_senate()` | Filter results to SC House and Senate only |
| `find_new_reports()` | Compare scraped IDs against state.json, apply House/Senate filter |
| `send_email_notification()` | Send formatted alert via Resend (or SendGrid fallback) |
| `load_state()` / `save_state()` | Persist seen report IDs |

**Key Configuration:**
```python
CAMPAIGN_REPORTS_URL = "https://ethicsfiling.sc.gov/public/campaign-reports/reports"
STATE_FILE = Path(__file__).parent.parent / "state.json"
max_pages = 3  # Scrapes recent Initial Reports

# House/Senate filtering patterns
HOUSE_SENATE_PATTERNS = [
    "house of representatives", "sc house", "state house",
    "senate", "sc senate", "state senate"
]
```

### 2. GitHub Actions: `.github/workflows/monitor.yml`

**Triggers:**
- Scheduled: `cron: '0 14 * * *'` (9 AM EST / 2 PM UTC)
- Manual: `workflow_dispatch` (can trigger from Actions tab)

**Required Secrets:**
| Secret | Description | Current Value |
|--------|-------------|---------------|
| `RESEND_API_KEY` | Resend API key for email | `re_YvUK2c6w_...` (set) |
| `NOTIFICATION_EMAIL` | Recipient email | `russell.teter@gmail.com` |
| `FROM_EMAIL` | Sender email | `onboarding@resend.dev` |
| `SENDGRID_API_KEY` | (Fallback) SendGrid key | Set but expired trial |

### 3. State File: `state.json`

**Structure:**
```json
{
  "seen_report_ids": ["414669", "412735", ...],
  "last_checked": "2026-01-08T22:28:34.123456Z"
}
```

**Important:** This file is auto-committed by the workflow after each run.

---

## Email Provider: Resend

**Status:** Active and working

**Why Resend (not SendGrid):**
- SendGrid trial expired November 25, 2025
- Resend free tier: 100 emails/day, 3,000/month
- Simple REST API, minimal code changes

**Current Sender:** `onboarding@resend.dev` (Resend test domain)

**To use custom domain:** Verify domain at https://resend.com/domains

---

## Common Tasks

### Trigger a Manual Run
```bash
gh workflow run monitor.yml --repo russellteter/sc-ethics-monitor
```

### Check Recent Workflow Runs
```bash
gh run list --repo russellteter/sc-ethics-monitor --limit 5
```

### View Workflow Logs
```bash
gh run view <run-id> --repo russellteter/sc-ethics-monitor --log
```

### Reset State (Force Email with All Reports)
```bash
# Get current SHA
SHA=$(gh api repos/russellteter/sc-ethics-monitor/contents/state.json --jq '.sha')

# Reset to empty
gh api repos/russellteter/sc-ethics-monitor/contents/state.json \
  --method PUT \
  -f message="Reset state for testing" \
  -f content="$(echo '{"seen_report_ids": [], "last_checked": null}' | base64)" \
  -f sha="$SHA"
```

### Update GitHub Secrets
```bash
gh secret set SECRET_NAME --repo russellteter/sc-ethics-monitor --body "value"
```

---

## Data Source Details

**Website:** https://ethicsfiling.sc.gov/public/campaign-reports/reports

**What's Monitored:**
- **Initial Reports only** - the first campaign disclosure when $500 is raised/spent
- **SC House and SC Senate candidates only** - County, Municipal, School Board excluded
- Current election year

**Why Initial Reports Matter:**
Initial Reports are the earliest official indicator that someone is serious about running. Before the $500 threshold, anyone can say they're "thinking about" running. The Initial Report proves they've started fundraising or spending.

**How Reports Are Identified:**
Each report has a unique `reportId` in the URL (e.g., `reportId=414669`). These IDs are stable and never reused.

**Filtering Logic:**
1. Website filter: Report Type = "Initial"
2. Post-scrape filter: Office must contain "house", "senate" (case-insensitive)

---

## Troubleshooting

### Email Not Sending

1. **Check Resend API key:** Verify `RESEND_API_KEY` secret is set
2. **Check FROM_EMAIL:** Must be `onboarding@resend.dev` or a verified domain
3. **Check logs:** `gh run view <id> --log | grep -i "email\|resend"`

### Scraper Failing

1. **Website changed:** SC Ethics may have updated their HTML structure
2. **Check selectors:** Review `scrape_recent_reports()` in monitor.py
3. **Test locally:** `python src/monitor.py` (requires Playwright installed)

### No New Reports Detected

This is normal if no new filings since last check. To force an email:
1. Reset state.json (see Common Tasks above)
2. Trigger manual workflow run

---

## Future Enhancement Ideas

- [ ] Filter for specific candidates or offices only
- [ ] Add SMS notifications (Twilio)
- [ ] Multiple check times per day
- [ ] Custom email templates with better formatting
- [ ] Dashboard showing historical filing data
- [ ] AI-powered analysis of filing contents

---

## Session History

**Initial Build:** January 2026
- Created scraper using Playwright
- Implemented change detection with state.json
- Set up GitHub Actions workflow
- Configured SendGrid (later replaced)

**SendGrid → Resend Migration:** January 8, 2026
- SendGrid trial expired, blocking all emails
- Migrated to Resend (free tier, 100/day)
- Using `onboarding@resend.dev` as sender
- Successfully tested with 45 filings

**Initial Report Focus:** January 8, 2026
- Refocused from all reports to **Initial Reports only**
- Added "Initial" report type filter to scraper
- Added House/Senate post-scrape filtering
- Updated email template for candidate tracking use case
- Verified spec against live website (all URL patterns work)

---

## Repository

- **GitHub:** https://github.com/russellteter/sc-ethics-monitor
- **Owner:** russellteter
- **Visibility:** Private

---

## Contact

- **Notification Recipient:** russell.teter@gmail.com
- **Resend Account:** (linked via GitHub OAuth)

# SC Ethics Initial Report Monitor - Project Context

## Quick Start for New Sessions

```bash
# This project monitors SC Ethics Commission for NEW CANDIDATE Initial Reports
# Target: SC House of Representatives only (124 districts)
# Purpose: Help party recruiters identify serious candidates early
# Repository: https://github.com/russellteter/sc-ethics-monitor
# Status: OPERATIONAL - Email notifications working via Resend
```

---

## Project Overview

| Attribute | Value |
|-----------|-------|
| **Purpose** | Detect new SC House candidates via Initial Report filings |
| **What's an Initial Report?** | First required filing when candidate raises/spends $500 |
| **Why it matters** | Earliest signal of serious candidate intent |
| **Primary Output** | Email alerts when new candidates file Initial Reports |
| **Scope** | SC House of Representatives only (124 districts) |
| **Schedule** | Daily at 7:00 PM EST (this repo) / 6:30 PM EDT (VREMS primary) |
| **Cost** | $0/month (free tier services) |
| **Status** | Production-ready, operational |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DAILY WORKFLOW                           │
├─────────────────────────────────────────────────────────────┤
│  GitHub Actions (7 PM EST)                                  │
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
│  Filter to House only (post-scrape)                         │
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

## Related Repos & Daily Pipeline

This repo is ONE part of a 3-repo system. Most work spans all three.

| Repo | Path | Purpose | Schedule (EDT) |
|------|------|---------|----------------|
| **sc-vrems-filing-monitor** | `~/Desktop/sc-vrems-filing-monitor` | Primary scraper + email (VREMS CSV data) | 6:30 PM |
| **sc-filing-coverage-map** | `~/Desktop/sc-filing-coverage-map` | Interactive district map (Next.js, GitHub Pages) | 6:10 PM |
| **sc-ethics-report-monitor** | `~/Desktop/sc-ethics-report-monitor` | This repo — Ethics Commission scraper (secondary) | 7:00 PM |

**Pipeline order:** Map refresh (6:10 PM) → VREMS scrape + email (6:30 PM)
Map must be fresh before email sends because recipients click the map link.

**Data flow:** VREMS CSV → state.json → generate-from-vrems.py → candidates.json → map
**Key distinction:** `candidates.json` = actual filings. `party-data.json` = static incumbent reference. Never mix them for status/coloring.

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
| `is_state_house()` | Filter results to SC House only (124 districts) |
| `find_new_reports()` | Compare scraped IDs against state.json, apply House filter |
| `build_email_template_a()` | Generate Locality AI branded HTML email (720px, teal palette) |
| `send_daily_digest()` | Merge data sources, select template, send via Resend |
| `send_test_emails()` | Send test email with mock data (--test-email CLI) |
| `format_candidate_name()` | Convert "Last, First M" → "First M Last" |
| `format_district()` | Extract "District 91" from full office string |
| `_district_competitor_count()` | Count other candidates in same district |
| `_days_since_filing()` | Human-readable age: "3d", "2w", "8mo" |
| `load_state()` / `save_state()` | Persist seen report IDs with validation |

**Key Configuration:**
```python
CAMPAIGN_REPORTS_URL = "https://ethicsfiling.sc.gov/public/campaign-reports/reports"
STATE_FILE = Path(__file__).parent.parent / "state.json"
max_pages = 3  # Scrapes recent Initial Reports

# House-only filtering patterns (scope narrowed March 2026)
STATE_HOUSE_PATTERNS = [
    "sc house of representatives",
    "house of representatives district",
]
```

### 2. GitHub Actions: `.github/workflows/monitor.yml`

**Triggers:**
- Scheduled: `cron: '0 0 * * *'` (7 PM EST / midnight UTC)
- Manual: `workflow_dispatch` (can trigger from Actions tab)

**Required Secrets:**
| Secret | Description | Current Value |
|--------|-------------|---------------|
| `RESEND_API_KEY` | Resend API key for email | `re_E9v9kKYM_...` (production, for `alerts@info.locality-ai.com`) |
| `NOTIFICATION_EMAIL` | Recipient email | `russell.teter@gmail.com` |
| `FROM_EMAIL` | Sender email | `alerts@info.locality-ai.com` |
| `SENDGRID_API_KEY` | (Fallback) SendGrid key | Set but expired trial |

**API Key Notes:**
- Production key `re_E9v9kKYM_9cm1pNZVf2cK5jg5NB2Y8x1H` works with verified domain `alerts@info.locality-ai.com`
- Test key `re_YvUK2c6w_...` only works with `onboarding@resend.dev` test sender

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

**Current Sender:** `alerts@info.locality-ai.com` (verified custom domain)

**Test Sender:** `onboarding@resend.dev` (Resend test domain, use with test key only)

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
- **SC House of Representatives candidates only** - Senate, County, Municipal, School Board excluded
- Current election year

**Why Initial Reports Matter:**
Initial Reports are the earliest official indicator that someone is serious about running. Before the $500 threshold, anyone can say they're "thinking about" running. The Initial Report proves they've started fundraising or spending.

**How Reports Are Identified:**
Each report has a unique `reportId` in the URL (e.g., `reportId=414669`). These IDs are stable and never reused.

**Filtering Logic:**
1. Website filter: Report Type = "Initial"
2. Post-scrape filter: Office must match SC House of Representatives patterns

---

## Troubleshooting

### Email Not Sending

1. **Check Resend API key:** Verify `RESEND_API_KEY` secret is set
2. **Check FROM_EMAIL:** Must be `alerts@info.locality-ai.com` or `onboarding@resend.dev` (with matching API key)
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

- [x] Custom email domain (`alerts@info.locality-ai.com` — verified)
- [ ] Add SMS notifications (Twilio)
- [ ] Multiple check times per day
- [ ] Dashboard showing historical filing data
- [ ] AI-powered analysis of filing contents
- [ ] Incumbent matching data integration

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

**House-Only Scope + Branded Templates:** March 8, 2026
- Narrowed scope from House & Senate to **SC House only** (124 districts)
- Renamed `is_house_or_senate()` → `is_state_house()`, updated patterns
- Removed Senate entries from state.json
- Built two email templates with **Locality AI branding** (teal palette, Syne font)
- **Template A selected** for production ("Daily Brief" layout)
- Template width: 720px for better table readability
- New data columns: Cycle (election year), In Dist (competitor count, red when >1), Age (time since filing)
- Header stats integrated: Tracked / Districts Active / Contested
- Subject line: `SC House Candidate Filings Report - N New Candidates Today - M/D`
- Schedule changed to **7 PM EST** (cron: 0 0 * * *)
- Added `--test-email` CLI mode with mock data
- Added retry logic, structured logging, state validation, party detection try/except
- Resend API requires `User-Agent` header to avoid Cloudflare 1010 blocks
- **Next**: 3/16 morning testing, then rewire NOTIFICATION_EMAIL to Brady for 7 PM launch

---

## Gotchas

- `sheets_sync.py` hangs on import when Google credentials aren't available — don't import it locally
- Resend API requires `User-Agent` header or Cloudflare blocks with error 1010
- `party-data.json` incumbents are reference context ONLY — never use them to determine filing status or coverage stats
- Coverage stats (Dem Filed, Coverage %, Gaps) are computed in 3 places in the map repo: `districtColors.ts`, `lensKpis.ts`, `PartyFilingSummary.tsx` — fix all or none
- Google Sheet ID: `1_SztBdJyl4FoPrtPiduKvrrnttisZDAJRLiHeoyFxLY`

---

## Repository

- **GitHub:** https://github.com/russellteter/sc-ethics-monitor
- **Owner:** russellteter
- **Visibility:** Private

---

## Contact

- **Production Recipients:** bradyqg@gmail.com, russell@locality-ai.com, taylor@taylorculliver.com
- **Resend Account:** (linked via GitHub OAuth)
- **Production API Key:** `re_E9v9kKYM_9cm1pNZVf2cK5jg5NB2Y8x1H` (for `alerts@info.locality-ai.com`)
- **Test API Key:** `re_YvUK2c6w_NP2geC7xwz9XKxK4nxiABadv` (for `onboarding@resend.dev` only)

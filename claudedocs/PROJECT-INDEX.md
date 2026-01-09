# SC Ethics Filing Monitor - Project Index

> Generated: January 8, 2026
> Status: Production (Operational)
> Token-Optimized Reference for Claude Sessions

---

## Quick Reference

| Item | Value |
|------|-------|
| **Repo** | `russellteter/sc-ethics-monitor` |
| **Main Script** | `src/monitor.py` |
| **Workflow** | `.github/workflows/monitor.yml` |
| **State** | `state.json` (auto-updated) |
| **Email** | Resend API (`onboarding@resend.dev`) |
| **Schedule** | Daily 9 AM EST |

---

## File Map

```
sc-ethics-report-monitor/
│
├── CLAUDE.md                           # [ENTRY POINT] Session context & instructions
├── README.md                           # User setup guide
├── requirements.txt                    # Dependencies: playwright, requests
├── state.json                          # Runtime state (seen report IDs)
│
├── src/
│   └── monitor.py                      # [CORE] All scraping/email logic (364 lines)
│
├── .github/workflows/
│   └── monitor.yml                     # GitHub Actions automation (47 lines)
│
├── docs/
│   └── SC-Ethics-Monitor-Overview.md   # Stakeholder documentation
│
└── claudedocs/
    ├── PROJECT-INDEX.md                # THIS FILE
    ├── FUNCTIONS.md                    # Function reference
    ├── WORKFLOW.md                     # GitHub Actions details
    └── CONFIGURATION.md                # Secrets & environment vars
```

---

## Component Summary

### `src/monitor.py` - Core Logic

**Purpose:** Scrape SC Ethics website, detect new filings, send email alerts

**Key Functions:**
| Function | Lines | Purpose |
|----------|-------|---------|
| `main()` | 298-363 | Entry point, orchestrates full workflow |
| `scrape_recent_reports()` | 54-179 | Playwright scraping, extracts ~45 reports |
| `send_email_notification()` | 216-275 | Builds email, routes to Resend/SendGrid |
| `_send_via_resend()` | 278-306 | Resend API call |
| `_send_via_sendgrid()` | 309-339 | SendGrid API call (fallback) |
| `find_new_reports()` | 207-211 | Compare report IDs against state |
| `load_state()` / `save_state()` | 182-204 | JSON state persistence |
| `extract_report_id()` | 48-51 | Parse reportId from URL |
| `get_statistics()` | 37-45 | Fetch daily activity counts (optional) |

**Dependencies:**
- `playwright.sync_api` - Browser automation
- `requests` - HTTP client for email APIs
- `json`, `os`, `re`, `sys`, `datetime`, `pathlib` - Standard library

### `.github/workflows/monitor.yml` - Automation

**Triggers:**
- `schedule: cron '0 14 * * *'` (9 AM EST)
- `workflow_dispatch` (manual)

**Steps:**
1. Checkout repository
2. Setup Python 3.11
3. Install dependencies + Playwright
4. Run monitor.py with secrets
5. Commit state.json changes

**Secrets Required:**
- `RESEND_API_KEY` - Email provider
- `NOTIFICATION_EMAIL` - Recipient
- `FROM_EMAIL` - Sender address

### `state.json` - Runtime State

**Schema:**
```json
{
  "seen_report_ids": ["string"],
  "last_checked": "ISO8601 timestamp"
}
```

**Behavior:** Auto-committed after each workflow run. Report IDs accumulate (never pruned).

---

## Data Flow

```
1. TRIGGER
   GitHub Actions (cron or manual)

2. SCRAPE
   Playwright → ethicsfiling.sc.gov
   └── Filter: current year
   └── Sort: Last Updated (desc)
   └── Pages: 3 (~45 reports)

3. EXTRACT
   For each row: reportId, candidate, office, report type, date, URL

4. COMPARE
   scraped_ids - seen_report_ids = new_reports

5. NOTIFY (if new_reports > 0)
   Resend API → email notification

6. PERSIST
   Update state.json → git commit → git push
```

---

## External Integrations

### SC Ethics Commission Website
- **URL:** `https://ethicsfiling.sc.gov/public/campaign-reports/reports`
- **API:** `https://ethicsfiling.sc.gov/api/Ethics/Get/Public/General/Statistics`
- **Access:** Public, no authentication
- **Method:** Playwright (JavaScript-rendered SPA)

### Resend (Email Provider)
- **API:** `https://api.resend.com/emails`
- **Auth:** Bearer token
- **Free Tier:** 100 emails/day, 3,000/month
- **Current Sender:** `onboarding@resend.dev`

### SendGrid (Fallback - Currently Expired)
- **API:** `https://api.sendgrid.com/v3/mail/send`
- **Status:** Trial expired Nov 25, 2025
- **Kept as:** Fallback option if Resend unavailable

---

## Common Operations

### Test Email Delivery
```bash
# Reset state to trigger email with all current filings
SHA=$(gh api repos/russellteter/sc-ethics-monitor/contents/state.json --jq '.sha')
gh api repos/russellteter/sc-ethics-monitor/contents/state.json \
  --method PUT -f message="Reset state" \
  -f content="$(echo '{"seen_report_ids": [], "last_checked": null}' | base64)" \
  -f sha="$SHA"
gh workflow run monitor.yml --repo russellteter/sc-ethics-monitor
```

### Check Workflow Status
```bash
gh run list --repo russellteter/sc-ethics-monitor --limit 3
gh run view <run-id> --log | grep -i "email\|error\|new report"
```

### Update Secrets
```bash
gh secret set RESEND_API_KEY --repo russellteter/sc-ethics-monitor
gh secret set NOTIFICATION_EMAIL --repo russellteter/sc-ethics-monitor
gh secret set FROM_EMAIL --repo russellteter/sc-ethics-monitor
```

### Local Testing
```bash
cd /Users/russellteter/Desktop/sc-ethics-report-monitor
pip install -r requirements.txt
playwright install chromium
export RESEND_API_KEY="re_..."
export NOTIFICATION_EMAIL="your@email.com"
export FROM_EMAIL="onboarding@resend.dev"
python src/monitor.py
```

---

## Known Limitations

1. **Single daily check** - Filings could be up to 24 hours old when detected
2. **No content analysis** - Reports contributions/expenditures not parsed
3. **All candidates** - No filtering by specific office or candidate
4. **Website dependent** - HTML structure changes require code updates
5. **State grows forever** - seen_report_ids list not pruned

---

## Cross-References

| Document | Purpose |
|----------|---------|
| [CLAUDE.md](../CLAUDE.md) | Session initialization, full context |
| [README.md](../README.md) | User-facing setup instructions |
| [docs/SC-Ethics-Monitor-Overview.md](../docs/SC-Ethics-Monitor-Overview.md) | Stakeholder documentation |
| [claudedocs/FUNCTIONS.md](FUNCTIONS.md) | Detailed function documentation |
| [claudedocs/WORKFLOW.md](WORKFLOW.md) | GitHub Actions reference |
| [claudedocs/CONFIGURATION.md](CONFIGURATION.md) | Environment & secrets guide |

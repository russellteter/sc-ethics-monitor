# SC Ethics Initial Report Monitor

Automated monitoring system for South Carolina Ethics Commission Initial Report filings. Detects new SC House of Representatives candidates and sends branded email notifications via Resend.

## What It Does

- Monitors [SC Ethics Filing Portal](https://ethicsfiling.sc.gov/public/campaign-reports/reports) for **Initial Reports** (first $500 disclosure)
- Filters to **SC House of Representatives only** (124 districts)
- Sends Locality AI branded email alerts when new candidates file
- Runs daily at 7:00 PM EST via GitHub Actions
- Part of a 3-repo system with [VREMS Filing Monitor](https://github.com/russellteter/sc-vrems-filing-monitor) and [Coverage Map](https://github.com/russellteter/sc-filing-coverage-map)

## How It Works

1. **Daily Trigger** — GitHub Actions runs at midnight UTC (7 PM EST)
2. **Scrape** — Playwright navigates Ethics portal, filters to "Initial" report type
3. **Filter** — Post-scrape filter to SC House candidates only
4. **Detect** — Compare report IDs against `state.json` to find new filings
5. **Notify** — Send formatted email via Resend API (`alerts@info.locality-ai.com`)
6. **Persist** — Commit updated `state.json` to repo

## Setup

### Prerequisites

- Python 3.11+
- [Resend](https://resend.com) account with verified domain

### Local Development

```bash
pip install -r requirements.txt
playwright install chromium

# Run monitor
python src/monitor.py

# Send test email
python src/monitor.py --test-email
```

### GitHub Secrets

| Secret | Description |
|--------|-------------|
| `RESEND_API_KEY` | Resend API key |
| `NOTIFICATION_EMAIL` | Comma-separated recipient emails |
| `FROM_EMAIL` | Verified sender (e.g., `alerts@info.locality-ai.com`) |
| `GOOGLE_SHEETS_CREDENTIALS` | Base64-encoded Google service account JSON |
| `GOOGLE_SHEET_ID` | Google Sheet for candidate tracker |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `RESEND_API_KEY` | Yes | Resend API key for email |
| `NOTIFICATION_EMAIL` | Yes | Recipient email(s), comma-separated |
| `FROM_EMAIL` | No | Sender address (default: `alerts@info.locality-ai.com`) |
| `ENVIRONMENT` | No | Set to `production` for real recipients |

## File Structure

```
sc-ethics-report-monitor/
├── .github/workflows/
│   └── monitor.yml              # GitHub Actions workflow (7 PM EST)
├── src/
│   ├── monitor.py               # Main script — scraping, filtering, templates, email
│   ├── config.py                # Environment config (optional import)
│   ├── party_detector.py        # Multi-source party detection
│   ├── incumbent_matcher.py     # Incumbent matching by district
│   ├── sheets_sync.py           # Google Sheets sync (optional import)
│   ├── backfill.py              # One-time historical data loader (standalone)
│   └── sources/                 # Party detection data sources
│       ├── ballotpedia.py       # Ballotpedia search
│       ├── party_sites.py       # SCDP/SCGOP website search
│       └── social_media.py      # Social media party signals
├── claudedocs/
│   └── SCRAPING-WORKFLOW.md     # Playwright scraper reference
├── state.json                   # Tracked report IDs (auto-committed)
├── CLAUDE.md                    # AI assistant project context
├── requirements.txt             # Python dependencies
└── sc-ethics-initial-report-spec.md  # Original specification
```

## Related Systems

| System | Repo | Purpose |
|--------|------|---------|
| **VREMS Monitor** | `sc-vrems-filing-monitor` | Primary production scraper + daily email |
| **Coverage Map** | `sc-filing-coverage-map` | Interactive district map (GitHub Pages) |
| **Google Sheet** | [Master Tracker](https://docs.google.com/spreadsheets/d/1_SztBdJyl4FoPrtPiduKvrrnttisZDAJRLiHeoyFxLY/) | Candidate data tracker |

## Troubleshooting

- **No email sent**: Check `RESEND_API_KEY` secret, verify sender domain, check Actions logs
- **Scraper fails**: SC Ethics site may have changed selectors — review `scrape_recent_reports()`
- **No new reports**: Normal if no filings since last check — reset `state.json` to force re-send
- **Resend 1010 error**: Must include `User-Agent` header in API calls (Cloudflare blocks without it)

## Legal

All data from the SC Ethics Commission is public information. The Ethics Commission states: "All forms and statements filed with the State Ethics Commission are public information open for public inspection."

## Cost

$0/month — GitHub Actions free tier + Resend free tier (100 emails/day).

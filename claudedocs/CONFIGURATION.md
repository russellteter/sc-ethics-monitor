# Configuration Reference

> Complete guide to environment variables, secrets, and configurable parameters

---

## Environment Variables

### Required for Email Notifications

| Variable | Description | Example |
|----------|-------------|---------|
| `RESEND_API_KEY` | Resend API key | `re_YvUK2c6w_NP2geC7xwz9XKxK4nxiABadv` |
| `NOTIFICATION_EMAIL` | Recipient email address | `russell.teter@gmail.com` |
| `FROM_EMAIL` | Sender email address | `onboarding@resend.dev` |

### Optional (Fallback)

| Variable | Description | Example |
|----------|-------------|---------|
| `SENDGRID_API_KEY` | SendGrid API key (fallback) | `SG.xxxxx...` |

---

## GitHub Secrets

Secrets are stored in the repository settings and injected at runtime.

### Current Configuration

```
Repository: russellteter/sc-ethics-monitor
Path: Settings → Secrets and variables → Actions
```

| Secret | Status | Value (partial) |
|--------|--------|-----------------|
| `RESEND_API_KEY` | Active | `re_YvUK2c6w_...` |
| `NOTIFICATION_EMAIL` | Active | `russell.teter@gmail.com` |
| `FROM_EMAIL` | Active | `onboarding@resend.dev` |
| `SENDGRID_API_KEY` | Set (expired) | `SG.oLTQbwZm...` |

### Managing Secrets via CLI

```bash
# List all secrets
gh secret list --repo russellteter/sc-ethics-monitor

# Set a secret interactively
gh secret set RESEND_API_KEY --repo russellteter/sc-ethics-monitor

# Set a secret from value
gh secret set FROM_EMAIL --body "notifications@yourdomain.com" --repo russellteter/sc-ethics-monitor

# Delete a secret
gh secret delete SENDGRID_API_KEY --repo russellteter/sc-ethics-monitor
```

---

## Configurable Parameters in Code

### `src/monitor.py`

| Parameter | Location | Default | Description |
|-----------|----------|---------|-------------|
| `max_pages` | Line 323 | `3` | Number of results pages to scrape (~15 reports/page) |
| `headless` | Line 320 | `True` | Run browser without visible window |
| `timeout` | Various | `30` | HTTP request timeout in seconds |

**To change max_pages:**
```python
# In main() function
reports = scrape_recent_reports(page, max_pages=5)  # Scrape 5 pages (~75 reports)
```

### `.github/workflows/monitor.yml`

| Parameter | Location | Default | Description |
|-----------|----------|---------|-------------|
| `cron` | Line 6 | `'0 14 * * *'` | Schedule (9 AM EST daily) |
| `python-version` | Line 25 | `'3.11'` | Python version |

---

## Email Provider Configuration

### Resend (Primary)

**Account:** Created via GitHub OAuth
**Dashboard:** https://resend.com/emails
**API Docs:** https://resend.com/docs

**Free Tier Limits:**
- 100 emails/day
- 3,000 emails/month
- Test domain: `onboarding@resend.dev`

**To Use Custom Domain:**
1. Go to https://resend.com/domains
2. Add your domain
3. Configure DNS records (DKIM, SPF)
4. Update `FROM_EMAIL` secret

### SendGrid (Fallback - Expired)

**Status:** Trial expired November 25, 2025
**Dashboard:** https://app.sendgrid.com

**To Reactivate:**
1. Upgrade to paid plan ($19.95/month minimum)
2. Or create new account for fresh trial

---

## State File Configuration

### `state.json`

**Location:** Repository root
**Updated by:** GitHub Actions workflow (auto-committed)

**Schema:**
```json
{
  "seen_report_ids": ["414669", "412735", "411870", ...],
  "last_checked": "2026-01-08T22:28:34.123456Z"
}
```

**Behavior:**
- Report IDs accumulate over time (never automatically pruned)
- `last_checked` updated on every run

**Manual Reset:**
```bash
# Get current SHA
SHA=$(gh api repos/russellteter/sc-ethics-monitor/contents/state.json --jq '.sha')

# Reset to empty state
gh api repos/russellteter/sc-ethics-monitor/contents/state.json \
  --method PUT \
  -f message="Reset state" \
  -f content="$(echo '{"seen_report_ids": [], "last_checked": null}' | base64)" \
  -f sha="$SHA"
```

---

## Website Selectors

The scraper uses these selectors to navigate the SC Ethics website. Update if website structure changes.

### Current Selectors (as of January 2026)

```python
# Year dropdown
year_dropdown = page.get_by_title("Election Year dropdown").get_by_role("listbox")

# Year option
page.get_by_role("option", name=current_year)

# Search button
page.get_by_role("button", name="Search")

# Sort header
page.get_by_text("Last Updated").first

# Results table
rows = page.locator("table").last.locator("tr")

# Report link (first link in row)
report_link = row.locator("a").first

# Candidate link (second link in row)
candidate_link = row.locator("a").nth(1)

# Next page button
next_button = page.get_by_title("Go to the next page")
```

---

## Local Development Setup

### Prerequisites

- Python 3.11+
- pip
- GitHub CLI (`gh`) for secret management

### Installation

```bash
cd /Users/russellteter/Desktop/sc-ethics-report-monitor

# Create virtual environment (optional)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

### Running Locally

```bash
# Set environment variables
export RESEND_API_KEY="re_YvUK2c6w_NP2geC7xwz9XKxK4nxiABadv"
export NOTIFICATION_EMAIL="your@email.com"
export FROM_EMAIL="onboarding@resend.dev"

# Run the monitor
python src/monitor.py
```

### Testing Without Email

Comment out or modify the email sending:

```python
# In main(), temporarily disable email:
if new_reports:
    log(f"Found {len(new_reports)} NEW report(s)!")
    for report in new_reports:
        log(f"  - {report['candidate_name']}: {report['report_name']}")
    # send_email_notification(new_reports)  # Commented out for testing
```

---

## Timezone Reference

| Zone | Offset | 9 AM Local = UTC |
|------|--------|------------------|
| EST (Winter) | UTC-5 | 14:00 UTC |
| EDT (Summer) | UTC-4 | 13:00 UTC |

**Current cron:** `0 14 * * *` = 9 AM EST year-round

**For DST-aware scheduling:** Use 13:00 UTC in summer, 14:00 UTC in winter, or accept 1-hour shift.

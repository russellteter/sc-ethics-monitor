# GitHub Actions Workflow Reference

> Documentation for `.github/workflows/monitor.yml`

---

## Overview

| Property | Value |
|----------|-------|
| **Name** | SC Ethics Filing Monitor |
| **Trigger** | Daily schedule + manual dispatch |
| **Runner** | `ubuntu-latest` |
| **Duration** | ~90 seconds typical |

---

## Complete Workflow File

```yaml
name: SC Ethics Filing Monitor

on:
  schedule:
    # Run daily at 9 AM EST (14:00 UTC)
    - cron: '0 14 * * *'

  # Allow manual trigger
  workflow_dispatch:

permissions:
  contents: write

jobs:
  monitor:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          playwright install chromium
          playwright install-deps chromium

      - name: Run monitor
        env:
          RESEND_API_KEY: ${{ secrets.RESEND_API_KEY }}
          SENDGRID_API_KEY: ${{ secrets.SENDGRID_API_KEY }}
          NOTIFICATION_EMAIL: ${{ secrets.NOTIFICATION_EMAIL }}
          FROM_EMAIL: ${{ secrets.FROM_EMAIL }}
        run: python src/monitor.py

      - name: Commit state changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add state.json
          git diff --staged --quiet || git commit -m "Update filing state [skip ci]"
          git push
```

---

## Triggers

### Scheduled (Cron)

```yaml
schedule:
  - cron: '0 14 * * *'
```

| Field | Value | Meaning |
|-------|-------|---------|
| Minute | 0 | At minute 0 |
| Hour | 14 | At 14:00 UTC |
| Day of Month | * | Every day |
| Month | * | Every month |
| Day of Week | * | Every day of week |

**Result:** Runs daily at 14:00 UTC = 9:00 AM EST / 10:00 AM EDT

### Manual Dispatch

```yaml
workflow_dispatch:
```

Enables the "Run workflow" button in GitHub Actions UI.

**CLI Trigger:**
```bash
gh workflow run monitor.yml --repo russellteter/sc-ethics-monitor
```

---

## Permissions

```yaml
permissions:
  contents: write
```

Required for the "Commit state changes" step to push updated state.json back to the repository.

---

## Job Steps

### 1. Checkout Repository

```yaml
- name: Checkout repository
  uses: actions/checkout@v4
```

Clones the repository to the runner. Uses v4 for latest features.

### 2. Set up Python

```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.11'
```

Installs Python 3.11. Version chosen for:
- Type hint support (list[dict] syntax)
- Stable Playwright compatibility
- Modern async features (though not currently used)

### 3. Install Dependencies

```yaml
- name: Install dependencies
  run: |
    pip install -r requirements.txt
    playwright install chromium
    playwright install-deps chromium
```

**requirements.txt contents:**
```
playwright>=1.40.0
requests>=2.31.0
```

**Playwright commands:**
- `playwright install chromium` - Downloads Chromium browser
- `playwright install-deps chromium` - Installs system dependencies (fonts, libraries)

### 4. Run Monitor

```yaml
- name: Run monitor
  env:
    RESEND_API_KEY: ${{ secrets.RESEND_API_KEY }}
    SENDGRID_API_KEY: ${{ secrets.SENDGRID_API_KEY }}
    NOTIFICATION_EMAIL: ${{ secrets.NOTIFICATION_EMAIL }}
    FROM_EMAIL: ${{ secrets.FROM_EMAIL }}
  run: python src/monitor.py
```

Executes the main monitoring script with secrets injected as environment variables.

### 5. Commit State Changes

```yaml
- name: Commit state changes
  run: |
    git config --local user.email "action@github.com"
    git config --local user.name "GitHub Action"
    git add state.json
    git diff --staged --quiet || git commit -m "Update filing state [skip ci]"
    git push
```

**Logic:**
1. Configure git identity for the commit
2. Stage state.json
3. Check if there are changes (`git diff --staged --quiet`)
4. If changes exist, commit with message "Update filing state [skip ci]"
5. Push to origin

**Note:** `[skip ci]` prevents this commit from triggering another workflow run.

---

## Secrets Configuration

| Secret | Required | Description |
|--------|----------|-------------|
| `RESEND_API_KEY` | Yes | Resend API key for email delivery |
| `SENDGRID_API_KEY` | No | SendGrid API key (fallback, currently expired) |
| `NOTIFICATION_EMAIL` | Yes | Email address to receive alerts |
| `FROM_EMAIL` | Yes | Sender email (must be verified or use `onboarding@resend.dev`) |

**Current Values:**
- `RESEND_API_KEY`: `re_YvUK2c6w_NP2geC7xwz9XKxK4nxiABadv`
- `NOTIFICATION_EMAIL`: `russell.teter@gmail.com`
- `FROM_EMAIL`: `onboarding@resend.dev`

**Manage Secrets:**
```bash
# List secrets (names only)
gh secret list --repo russellteter/sc-ethics-monitor

# Set a secret
gh secret set SECRET_NAME --repo russellteter/sc-ethics-monitor

# Set from value
gh secret set SECRET_NAME --body "value" --repo russellteter/sc-ethics-monitor
```

---

## Monitoring & Debugging

### View Recent Runs

```bash
gh run list --repo russellteter/sc-ethics-monitor --limit 5
```

Output example:
```
completed  success  SC Ethics Filing Monitor  main  workflow_dispatch  20833903569  1m33s
completed  success  SC Ethics Filing Monitor  main  schedule          20830123456  1m28s
```

### View Specific Run Logs

```bash
gh run view 20833903569 --repo russellteter/sc-ethics-monitor --log
```

### Filter Logs for Key Events

```bash
# Check email status
gh run view <id> --log | grep -i "email\|resend\|sendgrid"

# Check for new reports
gh run view <id> --log | grep -i "new report\|found.*new"

# Check for errors
gh run view <id> --log | grep -i "error\|fail\|exception"
```

### Download Run Logs

```bash
gh run download <run-id> --repo russellteter/sc-ethics-monitor
```

---

## Failure Scenarios

| Failure | Cause | Resolution |
|---------|-------|------------|
| Step 3 fails | Playwright install issue | Check GitHub Actions runner compatibility |
| Step 4 fails (scrape) | Website structure changed | Update selectors in monitor.py |
| Step 4 fails (email) | Invalid API key or rate limit | Check secrets, verify Resend account |
| Step 5 fails | Git push rejected | Manually pull/push to resolve conflicts |

---

## Customization

### Change Schedule

Edit the cron expression in `monitor.yml`:

```yaml
schedule:
  # Every 6 hours
  - cron: '0 */6 * * *'

  # Twice daily (6 AM and 6 PM EST)
  - cron: '0 11,23 * * *'

  # Weekdays only at 9 AM EST
  - cron: '0 14 * * 1-5'
```

### Add Slack Notification

```yaml
- name: Notify Slack on failure
  if: failure()
  run: |
    curl -X POST ${{ secrets.SLACK_WEBHOOK }} \
      -H 'Content-Type: application/json' \
      -d '{"text":"SC Ethics Monitor failed! Check GitHub Actions."}'
```

### Run on Multiple Schedules

```yaml
schedule:
  - cron: '0 14 * * *'  # 9 AM EST
  - cron: '0 22 * * *'  # 5 PM EST
```

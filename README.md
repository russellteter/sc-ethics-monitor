# SC Ethics Filing Monitor

Automated monitoring system for South Carolina Ethics Commission campaign disclosure reports. Sends email notifications when new filings are detected.

## Features

- Monitors the [SC Ethics Filing Portal](https://ethicsfiling.sc.gov/public/home) for new campaign reports
- Tracks filing state to detect new submissions
- Sends email notifications via SendGrid when new filings are detected
- Runs automatically via GitHub Actions (daily at 9 AM EST)
- Zero cost using GitHub Actions and SendGrid free tiers

## How It Works

1. **Daily Check**: GitHub Actions triggers the monitor script once per day
2. **Scrape Reports**: Uses Playwright to navigate the ethics filing website and extract recent campaign disclosure reports
3. **Change Detection**: Compares report IDs against stored state to identify new filings
4. **Email Alert**: Sends notification with details of new filings
5. **Update State**: Saves seen report IDs to prevent duplicate notifications

## Setup Instructions

### 1. Fork/Clone Repository

```bash
git clone https://github.com/yourusername/sc-ethics-report-monitor.git
cd sc-ethics-report-monitor
```

### 2. Set Up SendGrid (Free Tier)

1. Create a free account at [SendGrid](https://sendgrid.com/)
2. Generate an API key: Settings → API Keys → Create API Key
3. Verify a sender email address

### 3. Configure GitHub Secrets

Go to your repository's Settings → Secrets and variables → Actions, and add:

| Secret | Description |
|--------|-------------|
| `SENDGRID_API_KEY` | Your SendGrid API key |
| `NOTIFICATION_EMAIL` | Email address to receive alerts |
| `FROM_EMAIL` | Verified sender email in SendGrid |

### 4. Enable GitHub Actions

The workflow will run automatically once enabled. You can also trigger it manually from the Actions tab.

## Local Development

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Running Locally

```bash
# Set environment variables (optional for testing)
export SENDGRID_API_KEY="your-api-key"
export NOTIFICATION_EMAIL="your@email.com"

# Run the monitor
python src/monitor.py
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SENDGRID_API_KEY` | Yes* | SendGrid API key for email notifications |
| `NOTIFICATION_EMAIL` | Yes* | Email address to receive notifications |
| `FROM_EMAIL` | No | Sender email address (default: sc-ethics-monitor@example.com) |

*Required for email notifications; script will still run without them.

### Adjusting Monitoring Scope

Edit `src/monitor.py` to customize:

- **Number of pages to scrape**: Modify `max_pages` parameter in `scrape_recent_reports()` (default: 3)
- **Election year filter**: The script automatically uses the current year
- **Schedule**: Edit `.github/workflows/monitor.yml` cron expression

## Data Sources

- **Primary**: [SC Ethics Filing Portal](https://ethicsfiling.sc.gov/public/home)
- **API Endpoint**: `https://ethicsfiling.sc.gov/api/Ethics/Get/Public/General/Statistics`
- **Campaign Reports**: `https://ethicsfiling.sc.gov/public/campaign-reports/reports`

## File Structure

```
sc-ethics-report-monitor/
├── .github/
│   └── workflows/
│       └── monitor.yml        # GitHub Actions workflow
├── src/
│   └── monitor.py             # Main monitoring script
├── state.json                 # Tracked report IDs (auto-updated)
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Troubleshooting

### No email notifications received

1. Check that `SENDGRID_API_KEY` and `NOTIFICATION_EMAIL` are set correctly
2. Verify your SendGrid sender email is verified
3. Check GitHub Actions logs for errors

### Script fails to scrape

1. The website structure may have changed - check the SC Ethics portal manually
2. Playwright browser may need reinstallation
3. Check GitHub Actions logs for specific errors

### Getting duplicate notifications

1. The `state.json` file may have been reset
2. Check that the workflow commits state changes properly

## Legal Notes

- All data from the SC Ethics Commission is public information
- The Ethics Commission states: "All forms and statements filed with the State Ethics Commission are public information open for public inspection"
- This tool is for personal/professional monitoring, not commercial solicitation

## Cost

- **GitHub Actions**: Free tier (2,000 minutes/month for private repos, unlimited for public)
- **SendGrid**: Free tier (100 emails/day)
- **Total**: $0/month

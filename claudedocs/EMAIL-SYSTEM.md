# Email Notification System Documentation

> Technical documentation for the email alert system

---

## Overview

The email system sends HTML-formatted notifications when new campaign disclosure filings are detected. It supports two providers with automatic fallback.

---

## Provider Priority

```
1. Resend (Primary)     → If RESEND_API_KEY is set
2. SendGrid (Fallback)  → If only SENDGRID_API_KEY is set
```

**Current Status:**
- Resend: Active (free tier)
- SendGrid: Expired (trial ended Nov 25, 2025)

---

## Email Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      EMAIL WORKFLOW                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  send_email_notification(new_reports)                           │
│            │                                                    │
│            ▼                                                    │
│  ┌─────────────────────────────────────┐                        │
│  │ Check: NOTIFICATION_EMAIL set?      │                        │
│  │ Check: RESEND_API_KEY or            │                        │
│  │        SENDGRID_API_KEY set?        │                        │
│  └─────────────────┬───────────────────┘                        │
│                    │ Yes                                        │
│                    ▼                                            │
│  ┌─────────────────────────────────────┐                        │
│  │ Build subject line                  │                        │
│  │ "SC Ethics Monitor: N New Filing(s) │                        │
│  │  Detected"                          │                        │
│  └─────────────────┬───────────────────┘                        │
│                    │                                            │
│                    ▼                                            │
│  ┌─────────────────────────────────────┐                        │
│  │ Build plain text body               │                        │
│  │ (for email clients without HTML)    │                        │
│  └─────────────────┬───────────────────┘                        │
│                    │                                            │
│                    ▼                                            │
│  ┌─────────────────────────────────────┐                        │
│  │ Build HTML body                     │                        │
│  │ (formatted table with links)        │                        │
│  └─────────────────┬───────────────────┘                        │
│                    │                                            │
│                    ▼                                            │
│  ┌─────────────────────────────────────┐                        │
│  │ RESEND_API_KEY set?                 │                        │
│  └────────┬────────────────┬───────────┘                        │
│           │ Yes            │ No                                 │
│           ▼                ▼                                    │
│  ┌────────────────┐  ┌────────────────┐                         │
│  │ _send_via_     │  │ _send_via_     │                         │
│  │ resend()       │  │ sendgrid()     │                         │
│  └────────┬───────┘  └────────┬───────┘                         │
│           │                   │                                 │
│           └─────────┬─────────┘                                 │
│                     ▼                                           │
│  ┌─────────────────────────────────────┐                        │
│  │ Return True (success) or            │                        │
│  │ False (failure)                     │                        │
│  └─────────────────────────────────────┘                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Email Content Structure

### Subject Line

```
SC Ethics Monitor: {count} New Filing(s) Detected
```

Example: `SC Ethics Monitor: 3 New Filing(s) Detected`

### Plain Text Body

```
SC Ethics Filing Monitor has detected 3 new campaign disclosure report(s).

- Smith, John (SC House of Representatives District 45)
  Report: Quarter 4, 2025 Report
  Updated: Jan 8, 2026
  Link: https://ethicsfiling.sc.gov/public/.../report-detail?...&reportId=414669

- Johnson, Mary (SC Senate District 12)
  Report: Pre-Election (General) Report 2024
  Updated: Jan 8, 2026
  Link: https://ethicsfiling.sc.gov/public/.../report-detail?...&reportId=414670

...
```

### HTML Body

```html
<html>
<body>
<h2>SC Ethics Filing Monitor Alert</h2>
<p>Detected <strong>3</strong> new campaign disclosure report(s):</p>
<table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse;">
    <tr style="background-color: #f0f0f0;">
        <th>Candidate</th>
        <th>Office</th>
        <th>Report</th>
        <th>Updated</th>
        <th>Link</th>
    </tr>
    <tr>
        <td>Smith, John</td>
        <td>SC House of Representatives District 45</td>
        <td>Quarter 4, 2025 Report</td>
        <td>Jan 8, 2026</td>
        <td><a href="https://ethicsfiling.sc.gov/...">View</a></td>
    </tr>
    <!-- More rows... -->
</table>
<p><small>This is an automated notification from SC Ethics Filing Monitor.</small></p>
</body>
</html>
```

---

## Resend API Integration

### Endpoint

```
POST https://api.resend.com/emails
```

### Headers

```
Authorization: Bearer {RESEND_API_KEY}
Content-Type: application/json
```

### Request Body

```json
{
    "from": "onboarding@resend.dev",
    "to": ["russell.teter@gmail.com"],
    "subject": "SC Ethics Monitor: 3 New Filing(s) Detected",
    "text": "Plain text content...",
    "html": "<html>...</html>"
}
```

### Response Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Email queued |
| 201 | Success | Email sent |
| 400 | Bad request | Check payload format |
| 401 | Unauthorized | Invalid API key |
| 403 | Forbidden | Domain not verified |
| 429 | Rate limited | Wait and retry |

### Code Implementation

```python
def _send_via_resend(subject: str, text_content: str, html_content: str) -> bool:
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
```

---

## SendGrid API Integration (Fallback)

### Endpoint

```
POST https://api.sendgrid.com/v3/mail/send
```

### Request Body (Different Structure)

```json
{
    "personalizations": [
        {"to": [{"email": "russell.teter@gmail.com"}]}
    ],
    "from": {"email": "onboarding@resend.dev"},
    "subject": "SC Ethics Monitor: 3 New Filing(s) Detected",
    "content": [
        {"type": "text/plain", "value": "Plain text content..."},
        {"type": "text/html", "value": "<html>...</html>"}
    ]
}
```

### Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success (legacy) |
| 202 | Accepted (queued) |
| 401 | Invalid API key or expired |
| 403 | Forbidden |

---

## Sender Domain Configuration

### Current Setup

Using Resend's test domain: `onboarding@resend.dev`

**Limitations:**
- Emails may land in spam for some recipients
- "via resend.dev" appears in email headers
- Limited to 100 emails/day

### Custom Domain Setup (Optional)

To send from your own domain:

1. **Add domain in Resend:**
   - Go to https://resend.com/domains
   - Click "Add Domain"
   - Enter your domain (e.g., `locality-ai.com`)

2. **Configure DNS records:**
   ```
   Type: TXT
   Name: resend._domainkey
   Value: (provided by Resend)

   Type: TXT
   Name: @
   Value: v=spf1 include:_spf.resend.com ~all
   ```

3. **Update FROM_EMAIL secret:**
   ```bash
   gh secret set FROM_EMAIL --body "alerts@locality-ai.com" \
     --repo russellteter/sc-ethics-monitor
   ```

---

## Error Scenarios

### Missing Configuration

```python
if not NOTIFICATION_EMAIL:
    log("Email not configured - NOTIFICATION_EMAIL not set")
    return False

if not RESEND_API_KEY and not SENDGRID_API_KEY:
    log("Email not configured - set RESEND_API_KEY or SENDGRID_API_KEY")
    return False
```

### Domain Not Verified (Resend)

```
Resend failed: 403 - {"statusCode":403,"message":"The locality-ai.com domain is not verified..."}
```

**Fix:** Use `onboarding@resend.dev` or verify your domain.

### API Key Invalid/Expired

```
Resend failed: 401 - {"statusCode":401,"message":"API key is invalid"}
```

**Fix:** Generate new API key at https://resend.com/api-keys

### Rate Limited

```
Resend failed: 429 - {"message":"Rate limit exceeded"}
```

**Fix:** Wait and retry, or upgrade plan.

---

## Testing Email

### Method 1: Reset State (Production Test)

```bash
# Reset state to mark all reports as "new"
SHA=$(gh api repos/russellteter/sc-ethics-monitor/contents/state.json --jq '.sha')
gh api repos/russellteter/sc-ethics-monitor/contents/state.json \
  --method PUT \
  -f message="Reset for email test" \
  -f content="$(echo '{"seen_report_ids": [], "last_checked": null}' | base64)" \
  -f sha="$SHA"

# Trigger workflow
gh workflow run monitor.yml --repo russellteter/sc-ethics-monitor
```

### Method 2: Local Test

```python
# Add to monitor.py temporarily
if __name__ == "__main__":
    # Test email with fake data
    test_reports = [{
        "report_id": "999999",
        "report_name": "Test Report",
        "candidate_name": "Test Candidate",
        "office": "Test Office",
        "election_year": "2025",
        "election_type": "General",
        "last_updated": "Jan 8, 2026",
        "url": "https://example.com"
    }]
    send_email_notification(test_reports)
```

---

## Future Enhancements

- [ ] HTML email templates with better styling
- [ ] Configurable email frequency (digest mode)
- [ ] Multiple recipient support
- [ ] SMS notifications via Twilio
- [ ] Slack webhook integration
- [ ] Email delivery tracking/analytics

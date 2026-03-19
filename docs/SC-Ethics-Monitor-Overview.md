# SC Ethics Filing Monitor
## Project Overview for Stakeholders

---

### What Is This?

The SC Ethics Initial Report Monitor is an automated system that watches the South Carolina Ethics Commission website for new **Initial Report** filings — the first campaign disclosure required when a candidate raises or spends $500. It sends branded email alerts when new SC House of Representatives candidates file.

**In simple terms:** This system automatically detects when someone becomes a serious candidate for the SC House by filing their first financial disclosure, and immediately notifies you via email.

---

### Why Does This Exist?

The SC Ethics Commission does not offer any notification service. If you want to know when a candidate files a new campaign finance report, your only options are:

1. Check the website manually (tedious, easy to miss filings)
2. Submit a FOIA request for bulk data (10+ business day response time)
3. Use this automated monitor (instant notification)

---

### What Does It Monitor?

The system monitors **Initial Reports** filed with the SC Ethics Commission — the first required campaign disclosure when a candidate raises or spends $500. This is the earliest official signal that someone is serious about running.

**Scope:** SC House of Representatives only (124 districts). Senate, County, Municipal, and Statewide candidates are filtered out.

---

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                         DAILY PROCESS                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   7:00 PM EST                                                   │
│      │                                                          │
│      ▼                                                          │
│   ┌─────────────────────┐                                       │
│   │  GitHub Actions     │  Automated scheduler triggers         │
│   │  starts the job     │  the monitoring script                │
│   └──────────┬──────────┘                                       │
│              │                                                  │
│              ▼                                                  │
│   ┌─────────────────────┐                                       │
│   │  Open SC Ethics     │  Navigate to the public               │
│   │  Commission website │  campaign reports page                │
│   └──────────┬──────────┘                                       │
│              │                                                  │
│              ▼                                                  │
│   ┌─────────────────────┐                                       │
│   │  Search for filings │  Filter by current year,              │
│   │  from current year  │  sort by most recent                  │
│   └──────────┬──────────┘                                       │
│              │                                                  │
│              ▼                                                  │
│   ┌─────────────────────┐                                       │
│   │  Extract report     │  Candidate name, office,              │
│   │  details            │  report type, date, link              │
│   └──────────┬──────────┘                                       │
│              │                                                  │
│              ▼                                                  │
│   ┌─────────────────────┐                                       │
│   │  Compare against    │  "Have we seen this                   │
│   │  previous filings   │  report ID before?"                   │
│   └──────────┬──────────┘                                       │
│              │                                                  │
│         ┌────┴────┐                                             │
│         │         │                                             │
│    NEW FILINGS   NO NEW                                         │
│         │       FILINGS                                         │
│         ▼         │                                             │
│   ┌───────────┐   │                                             │
│   │Send email │   │  Done for today                             │
│   │alert      │   │                                             │
│   └───────────┘   │                                             │
│         │         │                                             │
│         ▼         ▼                                             │
│   ┌─────────────────────┐                                       │
│   │  Save updated list  │  Remember what we've seen             │
│   │  of seen reports    │  to avoid duplicate alerts            │
│   └─────────────────────┘                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### The Scraping Process (More Detail)

**Step 1: Navigate to the Website**

The system uses a tool called Playwright, which is essentially a programmable web browser. It opens the SC Ethics Commission's campaign reports page just like you would in Chrome or Safari.

**Step 2: Apply Filters**

The system clicks the "Election Year" dropdown and selects the current year (2025), then clicks "Search" - exactly as a human would.

**Step 3: Sort Results**

It clicks the "Last Updated" column header twice to sort by most recently filed first. This ensures we always see the newest filings at the top.

**Step 4: Read the Results Table**

The system reads through the results table row by row, extracting:
- Report Name (e.g., "Quarter 4, 2025 Report")
- Candidate Name (e.g., "Smith, John")
- Office (e.g., "SC House of Representatives District 45")
- Election Year and Type
- Last Updated Date
- A unique Report ID from the link URL

**Step 5: Check Multiple Pages**

By default, the system reads the first 3 pages of results (~45 reports). This catches all recent filings even on high-volume days.

**Step 6: Compare to History**

Each report has a unique ID number assigned by the Ethics Commission. The system maintains a list of all report IDs it has ever seen. Any ID not on that list is a "new" filing.

**Step 7: Send Notification**

If new filings are found, an email is sent with a table showing all the new reports, including direct links to view each filing on the official website.

---

### How Do We Know It's Reliable?

**1. Unique Identifiers**

Every report in the Ethics Commission system has a unique numeric ID (e.g., `reportId=12345`). This ID never changes for a given report. We track these IDs to ensure we never miss a filing and never send duplicate alerts.

**2. Persistent State**

The list of "seen" report IDs is saved to a file after every run. This file persists between runs, so even if the system restarts or encounters an error, it remembers what it has already seen.

**3. Sorted by Recency**

By sorting results by "Last Updated" descending, we always see the newest filings first. Even if many reports are filed on the same day, we capture them all.

**4. Multiple Pages**

We don't just look at the first page of results. The system checks 3 pages (~45 reports) to ensure we catch everything, even during high-volume filing periods like quarterly deadlines.

**5. Error Handling**

If the scraping fails (website down, structure changed, network error), the system exits with an error code. It does NOT silently fail - the GitHub Actions log will show the failure, and no false "no new filings" state is saved.

**6. Logging**

Every run produces detailed logs showing:
- How many reports were found
- Which reports are new vs. already seen
- Whether the email was sent successfully
- Any errors or warnings

---

### What Is the Data Source?

**Official Source:** South Carolina Ethics Commission
**Website:** https://ethicsfiling.sc.gov/public/campaign-reports/reports
**Data Type:** Public campaign disclosure reports

The Ethics Commission states:
> "All forms and statements filed with the State Ethics Commission are public information open for public inspection."

This is publicly available data. The system simply automates the process of checking for new filings.

---

### Technical Infrastructure

| Component | Service | Cost |
|-----------|---------|------|
| Automation/Hosting | GitHub Actions | Free |
| Email Delivery | Resend | Free (up to 100/day) |
| State Storage | JSON file in repository | Free |
| **Total Monthly Cost** | | **$0** |

The system runs entirely on free tiers and requires no ongoing maintenance costs.

---

### Email Notifications

When new candidates file, you receive a branded Locality AI email with:

- **Header stats:** Dem Filed, Coverage %, Gaps, New Today
- **Filed Today table:** New candidates with district, party, filed date
- **All Tracked table:** Complete candidate list with filing age and competitor count
- **Quick links:** Interactive Coverage Map + Google Sheet tracker

The email uses a teal/dark palette (Syne font) and is designed for 720px readability.

---

### Limitations & Considerations

**What This Does NOT Do:**
- Download or store the actual report documents
- Analyze the contents of filings (contributions, expenditures)
- Track changes/amendments to existing reports
- Monitor lobbyist disclosures or SEI (Statement of Economic Interest) reports
- Provide historical data or trends

**Potential Points of Failure:**
- If the Ethics Commission redesigns their website, the scraper may need updates
- If the website is down during the scheduled check, that day's check will fail
- Email delivery depends on Resend's service availability

**Mitigation:**
- GitHub Actions logs show all failures clearly
- The system can be manually triggered at any time
- Multiple daily runs could be added if higher reliability is needed

---

### Current Configuration

| Setting | Value |
|---------|-------|
| Check Frequency | Once daily at 7:00 PM EST |
| Report Type | Initial Reports only (first $500 disclosure) |
| Scope | SC House of Representatives (124 districts) |
| Reports Checked | ~45 most recent (3 pages) |
| Notification Method | Email via Resend (`alerts@info.locality-ai.com`) |

---

### Questions?

**Q: How quickly will I know about a new filing?**
A: Within 24 hours. The system runs once daily at 7 PM EST. If a report is filed during the day, you'll know by that evening.

**Q: Can we check more frequently?**
A: Yes. The schedule can be changed to run multiple times per day (e.g., every 6 hours) with a simple configuration change.

**Q: What if I want to monitor specific candidates only?**
A: The system currently monitors all candidates. Filtering for specific candidates would require code modifications.

**Q: Is this legal?**
A: Yes. The data is explicitly public record. The system accesses only the public-facing website and does not circumvent any access controls.

**Q: Who maintains this?**
A: The system is largely self-maintaining. The only maintenance required is if the Ethics Commission significantly changes their website structure.

---

### Summary

This is a simple, free, automated monitoring system that:

1. Checks the SC Ethics Commission website daily
2. Identifies newly filed campaign disclosure reports
3. Sends an email notification with details and links

It replaces the tedious manual process of checking the website and ensures you never miss a new filing.

---

*Document prepared: January 2026, updated March 2026*
*System Status: Operational — sending daily to production recipients*

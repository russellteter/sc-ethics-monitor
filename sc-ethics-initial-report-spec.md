# SC Ethics Monitor - Refined Specification: Initial Report Detection

## Verification Status

> **VERIFIED: January 8, 2026**
>
> This specification was validated against the live SC Ethics Commission website using automated browser testing.

| Item | Status | Notes |
|------|--------|-------|
| URL structures | **VERIFIED** | All URL patterns work as documented |
| Report type terminology | **VERIFIED** | System uses "Initial" (stakeholder says "preliminary" - same thing) |
| Report type filtering | **VERIFIED** | Dropdown filter for "Initial" works |
| Office type filtering | **NOT AVAILABLE** | Website has no dropdown for House/Senate - post-scrape filtering required |
| Data extraction | **VERIFIED** | All fields (candidate, office, report type, date, URL) extractable |

---

## Executive Summary

**What we're building:** An automated alert system that detects when candidates file their **"Initial Report"** with the SC Ethics Commission - the first legally-required campaign finance disclosure that signals serious intent to run for office.

**Why it matters:** This is the earliest reliable indicator that someone is actually running (not just "thinking about it"). Party recruiters use this to identify where candidates exist and where recruitment gaps remain.

---

## The Specific Filing Type: "Initial Report"

### What It Is

The **"Initial Report"** (sometimes referred to as a "Preliminary Report" in conversation) is a specific campaign disclosure filing required when a candidate **first raises or spends $500** toward their campaign.

### Key Characteristics

| Attribute | Value |
|-----------|-------|
| **Report Name in System** | "Initial Report [YEAR]" (e.g., "Initial Report 2022", "Initial Report 2026") |
| **Trigger** | Candidate raises OR spends $500 |
| **Timing** | Filed within 10 days of crossing the $500 threshold |
| **Significance** | First required filing = serious candidate |

### What It Is NOT

- ❌ "Quarter 1/2/3/4 Report" - periodic ongoing filings
- ❌ "Pre-Election Report" - filed before election deadlines
- ❌ "Year-End Report" - annual summary
- ❌ "Statement of Economic Interests" - personal financial disclosure (different system)

These other report types are from **established candidates** already in the system. The Initial Report is the **entry point**.

---

## URL Structure Analysis

### Candidate Reports List
```
https://ethicsfiling.sc.gov/public/candidates-public-officials/person/campaign-disclosure-reports/reports?personId={personId}&seiId={seiId}&officeId={officeId}
```

**Parameters:**
- `personId` - Unique identifier for the individual
- `seiId` - Statement of Economic Interests ID (links person to their SEI filing)
- `officeId` - Unique identifier for the specific office/seat they're running for

**Example:** District 75 House candidate
```
https://ethicsfiling.sc.gov/public/candidates-public-officials/person/campaign-disclosure-reports/reports?personId=45921&seiId=51547&officeId=71866
```

### Specific Report Detail
```
https://ethicsfiling.sc.gov/public/candidates-public-officials/person/campaign-disclosure-reports/report-detail?personId={personId}&seiId={seiId}&officeId={officeId}&reportId={reportId}
```

**Additional Parameter:**
- `reportId` - Unique identifier for the specific report filing

**Example:** Initial Report 2022 for District 75 House candidate
```
https://ethicsfiling.sc.gov/public/candidates-public-officials/person/campaign-disclosure-reports/report-detail?personId=45921&seiId=51547&officeId=71866&reportId=357468
```

---

## Search/Filter Criteria

### Target Offices (Scope)

The request specifically mentions "SC Statehouse" which includes:

| Office Type | Description |
|-------------|-------------|
| **SC House of Representatives** | 124 districts (District 1-124) |
| **SC Senate** | 46 districts (District 1-46) |

**Note:** The requester mentioned "statehouse (or anything below)" - confirm if they also want:
- County offices
- Municipal offices
- School board
- Other local seats

For now, assume **SC House + SC Senate only** unless expanded.

### Target Report Type

**Filter for reports where the report name/type contains:**
- "Initial Report"

**Exclude:**
- "Quarter" (Q1, Q2, Q3, Q4, Quarter 1, etc.)
- "Pre-Election"
- "Year-End"
- "Amended" (unless it's "Amended Initial Report")

### Time Sensitivity Windows

| Period | Value | Notes |
|--------|-------|-------|
| **Jan 1 - Mar 15 (even years)** | HIGHEST | Pre-filing deadline rush |
| **Odd years** | HIGH | Early movers for next cycle |
| **Mar 16 - Dec (even years)** | MEDIUM | Post-filing, fewer new entrants |

---

## Data Points to Capture Per Alert

When a new Initial Report is detected, the alert should include:

| Field | Description | Example |
|-------|-------------|---------|
| **Candidate Name** | Full name | "John Smith" |
| **Office/Seat** | What they're running for | "SC House of Representatives District 75" |
| **Report Type** | Should always be Initial Report | "Initial Report 2026" |
| **Filing Date** | When it was filed/updated | "Jan 8, 2026" |
| **Direct Link** | URL to the report detail | Full URL with all parameters |

### Optional/Nice-to-Have
- Party affiliation (if available)
- District location/county
- Link to candidate's full profile

---

## Technical Implementation Notes

### The SPA Challenge

The site (`ethicsfiling.sc.gov`) is a JavaScript Single Page Application. Direct HTTP requests return only:
```html
<title>SC Ethics Filing</title>
Loading...
```

**Solution:** Headless browser automation (Puppeteer, Playwright) is required to:
1. Load the page
2. Wait for JavaScript to render
3. Extract the data from the DOM or intercept API calls

### Likely Underlying API

SPAs typically call JSON APIs. The headless browser approach should include network interception to discover if there's an underlying API like:
```
https://ethicsfiling.sc.gov/api/candidates/search
https://ethicsfiling.sc.gov/api/reports/list
```

If found, direct API calls would be more efficient than DOM scraping.

### Change Detection Strategy

Since there's no "recent filings" feed, the system must:

1. **Periodically query** for SC House + Senate candidates
2. **Extract all report listings** for each candidate
3. **Filter for "Initial Report" types**
4. **Compare against previously seen reports** (by reportId)
5. **Alert on new reportIds** not in the seen list
6. **Update the seen list**

**State Storage:** Track seen `reportId` values in a persistent store (SQLite, JSON file, etc.)

---

## Business Context: Why This Matters

### The Old Way (Pre-Legal Change)
Candidates had to file a declaration of intent with their party. Party recruiters could easily see who was running.

### The Current Reality
That requirement was struck down. Now:
- Anyone can say they're "thinking about running"
- No formal declaration until the March 15 filing deadline
- The **Initial Report** (triggered by $500 raised/spent) is the only early signal of serious intent

### The Manual Process Being Replaced
> "So now those of us working on recruitment are left to scan the ethics site and call around - it's super old school"

This automation replaces hours of manual site scanning with instant alerts.

---

## Validation Checklist

Implementation status:

- [x] System correctly identifies "Initial Report" as distinct from other report types
- [x] Filters are limited to SC House and SC Senate via post-scrape filtering
- [x] Alerts include all required data points (candidate, office, report, date, URL)
- [x] State tracking prevents duplicate alerts for the same report
- [x] System can run on a schedule (daily via GitHub Actions)
- [x] Alert delivery mechanism works (email via Resend API)

---

## Example Alert Format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 NEW CANDIDATE INITIAL REPORT DETECTED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Candidate:  Jane Doe
Office:     SC House of Representatives District 75
Report:     Initial Report 2026
Filed:      January 8, 2026

View Report:
https://ethicsfiling.sc.gov/public/candidates-public-officials/person/campaign-disclosure-reports/report-detail?personId=XXXXX&seiId=XXXXX&officeId=XXXXX&reportId=XXXXX

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This indicates the candidate has raised or spent
at least $500 and filed their first required
campaign disclosure.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Open Questions for Requester

1. **Scope confirmation:** SC House + SC Senate only, or also county/municipal/school board?
2. **Alert frequency:** Daily check sufficient, or more frequent during Jan-Mar?
3. **Historical backfill:** Want alerts for Initial Reports filed in the past X days, or only going forward?
4. **Multiple recipients:** Should alerts go to one person or a distribution list?

---

## Summary

| Attribute | Value |
|-----------|-------|
| **Target Report Type** | "Initial Report [YEAR]" |
| **Target Offices** | SC House (124 districts) + SC Senate (46 districts) |
| **Detection Method** | Monitor for new `reportId` values with "Initial Report" type |
| **Alert Trigger** | New Initial Report not previously seen |
| **Key Value** | Early signal of serious candidate intent (crossed $500 threshold) |

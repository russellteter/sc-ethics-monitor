# Scraping Workflow Documentation

> Technical deep-dive into how the SC Ethics website scraping works

---

## Overview

The scraper uses **Playwright** (headless Chromium) to navigate the SC Ethics Commission's JavaScript-rendered Single Page Application (SPA) and extract campaign disclosure report data.

---

## Why Playwright?

The SC Ethics website (`ethicsfiling.sc.gov`) is a modern Angular SPA that:
- Renders content via JavaScript (no static HTML)
- Uses dynamic dropdowns and AJAX-loaded tables
- Requires click interactions to filter/sort data

**Simple HTTP requests won't work** because the content doesn't exist until JavaScript executes.

---

## Scraping Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SCRAPE WORKFLOW                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. LAUNCH BROWSER                                                  │
│     ┌─────────────────────────────────────┐                         │
│     │ browser = chromium.launch(          │                         │
│     │   headless=True                     │                         │
│     │ )                                   │                         │
│     │ page = browser.new_page()           │                         │
│     └─────────────────────────────────────┘                         │
│                      │                                              │
│                      ▼                                              │
│  2. NAVIGATE TO REPORTS PAGE                                        │
│     ┌─────────────────────────────────────┐                         │
│     │ page.goto(CAMPAIGN_REPORTS_URL)     │                         │
│     │ page.wait_for_load_state(           │                         │
│     │   "networkidle"                     │                         │
│     │ )                                   │                         │
│     └─────────────────────────────────────┘                         │
│                      │                                              │
│                      ▼                                              │
│  3. SET YEAR FILTER                                                 │
│     ┌─────────────────────────────────────┐                         │
│     │ year_dropdown.click()               │                         │
│     │ page.get_by_role("option",          │                         │
│     │   name="2025").click()              │                         │
│     └─────────────────────────────────────┘                         │
│                      │                                              │
│                      ▼                                              │
│  4. EXECUTE SEARCH                                                  │
│     ┌─────────────────────────────────────┐                         │
│     │ page.get_by_role("button",          │                         │
│     │   name="Search").click()            │                         │
│     │ page.wait_for_load_state(           │                         │
│     │   "networkidle"                     │                         │
│     │ )                                   │                         │
│     └─────────────────────────────────────┘                         │
│                      │                                              │
│                      ▼                                              │
│  5. SORT BY LAST UPDATED (DESC)                                     │
│     ┌─────────────────────────────────────┐                         │
│     │ header = page.get_by_text(          │                         │
│     │   "Last Updated").first             │                         │
│     │ header.click()  # Ascending         │                         │
│     │ header.click()  # Descending        │                         │
│     └─────────────────────────────────────┘                         │
│                      │                                              │
│                      ▼                                              │
│  6. EXTRACT TABLE ROWS (Loop)                                       │
│     ┌─────────────────────────────────────┐                         │
│     │ for page_num in range(max_pages):   │                         │
│     │   rows = page.locator("table")      │                         │
│     │     .last.locator("tr")             │                         │
│     │   for row in rows:                  │                         │
│     │     extract_report_data(row)        │                         │
│     │   click_next_page()                 │                         │
│     └─────────────────────────────────────┘                         │
│                      │                                              │
│                      ▼                                              │
│  7. CLOSE BROWSER                                                   │
│     ┌─────────────────────────────────────┐                         │
│     │ browser.close()                     │                         │
│     │ return reports                      │                         │
│     └─────────────────────────────────────┘                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Extraction Details

### Table Structure

The results table has this structure:

```html
<table>
  <thead>
    <tr>
      <th>Report Name</th>
      <th>Candidate Name</th>
      <th>Office</th>
      <th>Election Year</th>
      <th>Election Type</th>
      <th>Last Updated</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><a href="/report-detail?...&reportId=414669">Quarter 4, 2025 Report</a></td>
      <td><a href="/person/...">Smith, John</a></td>
      <td>SC House of Representatives District 45</td>
      <td>2025</td>
      <td>General</td>
      <td>Jan 8, 2026</td>
    </tr>
    <!-- More rows... -->
  </tbody>
</table>
```

### Extraction Logic

```python
# For each row in the table
row = rows.nth(i)
cells = row.locator("td, gridcell")

# Skip header rows (less than 6 cells)
if cells.count() < 6:
    continue

# Extract links
report_link = row.locator("a").first
report_url = report_link.get_attribute("href")
report_name = report_link.text_content()

candidate_link = row.locator("a").nth(1)
candidate_name = candidate_link.text_content()

# Extract text cells
office = cells.nth(2).text_content()
election_year = cells.nth(3).text_content()
election_type = cells.nth(4).text_content()
last_updated = cells.nth(5).text_content()

# Parse report ID from URL
report_id = extract_report_id(report_url)  # Uses regex: r'reportId=(\d+)'
```

### Output Data Structure

```python
{
    "report_id": "414669",           # Unique identifier (from URL)
    "report_name": "Quarter 4, 2025 Report",
    "candidate_name": "Smith, John",
    "office": "SC House of Representatives District 45",
    "election_year": "2025",
    "election_type": "General",
    "last_updated": "Jan 8, 2026",
    "url": "https://ethicsfiling.sc.gov/public/.../report-detail?...&reportId=414669"
}
```

---

## Pagination Handling

The website displays ~15 reports per page. The scraper handles pagination:

```python
for page_num in range(max_pages):
    # Extract current page data
    extract_rows()

    # Try to go to next page
    if page_num < max_pages - 1:
        next_button = page.get_by_title("Go to the next page")
        if next_button.is_enabled():
            next_button.click()
            page.wait_for_timeout(1000)
        else:
            break  # No more pages
```

**Default:** 3 pages = ~45 reports

---

## Wait Strategies

The scraper uses multiple wait strategies for reliability:

| Strategy | Purpose | Usage |
|----------|---------|-------|
| `wait_for_load_state("networkidle")` | Wait for all network requests to complete | After navigation, after search |
| `wait_for_timeout(500-1000)` | Fixed delay for UI animations | After dropdown clicks, pagination |

---

## Error Handling

```python
try:
    # Attempt extraction
    report_link = row.locator("a").first
    report_url = report_link.get_attribute("href")
except Exception as e:
    log(f"Warning: Error extracting row {i}: {e}")
    continue  # Skip this row, continue with others
```

**Philosophy:** Log warnings but don't fail the entire scrape for individual row errors.

---

## Selector Reference

| Element | Selector | Method |
|---------|----------|--------|
| Year dropdown | `get_by_title("Election Year dropdown").get_by_role("listbox")` | Title + role |
| Year option | `get_by_role("option", name="2025")` | Role + name |
| Search button | `get_by_role("button", name="Search")` | Role + name |
| Last Updated header | `get_by_text("Last Updated").first` | Text content |
| Results table | `locator("table").last` | Tag + position |
| Table rows | `locator("tr")` | Tag |
| Links in row | `locator("a").first` / `.nth(1)` | Tag + index |
| Next page | `get_by_title("Go to the next page")` | Title |

---

## Maintenance Notes

### If Website Changes

1. **Check selectors:** Use Playwright Inspector (`playwright codegen`) to identify new selectors
2. **Test locally:** Run with `headless=False` to see browser actions
3. **Update wait times:** May need longer waits for slower page loads

### Common Failures

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| No reports found | Selector changed | Update table/row selectors |
| Year filter fails | Dropdown structure changed | Update year dropdown selector |
| All reports empty | Row extraction broken | Check cell indices |
| Timeout errors | Page loads slower | Increase wait times |

---

## Performance

| Metric | Typical Value |
|--------|---------------|
| Browser launch | ~2 seconds |
| Page navigation | ~3 seconds |
| Search execution | ~2 seconds |
| Per-page extraction | ~1 second |
| Total (3 pages) | ~15 seconds |
| Full workflow | ~90 seconds (including email) |

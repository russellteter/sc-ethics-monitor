# SC Ethics Initial Report Monitor — Project Index

> Auto-generated March 18, 2026. Source of truth for code structure and module relationships.

---

## Architecture

```
GitHub Actions (7 PM EST) → monitor.py
  ├─ Playwright → ethicsfiling.sc.gov (Initial Reports, SC House only)
  ├─ Dedup against state.json (seen_report_ids)
  ├─ Party detection (incumbent_matcher → party_detector → Firecrawl)
  ├─ Email via Resend (alerts@info.locality-ai.com)
  ├─ Google Sheets sync (optional)
  └─ Save state.json → git commit
```

**Related repos:** See CLAUDE.md § Related Repos & Daily Pipeline.

---

## Source Files (3,321 lines total)

### `src/monitor.py` — Core Engine (1,622 lines)

The single main script. All workflow logic lives here.

| Category | Functions |
|----------|-----------|
| **Scraping** | `scrape_recent_reports()` — Playwright 3-page scrape with Initial filter |
| | `scrape_2025_calendar_year()` — Historical 2025 data |
| **Filtering** | `is_state_house(office)` — House-only filter (124 districts) |
| **Detection** | `find_new_reports(reports, state)` — Dedup via reportId |
| | `detect_parties_for_candidates(candidates)` — Batch party detection |
| **Email** | `build_email_template_a()` — Production template (Locality AI, 720px, teal) |
| | `build_email_template_b()` — Alternative layout (not used) |
| | `send_daily_digest()` — Orchestrator: gate on new data, build HTML, send |
| | `_send_via_resend()` — Resend API with User-Agent header |
| | `_send_via_sendgrid()` — SendGrid fallback |
| **Formatting** | `format_candidate_name()` — "Last, First M" → "First M Last" |
| | `format_district()` — Extract "District 91" from office string |
| | `_party_badge_html()` — Colored D/R badge |
| | `_days_since_filing()` — "3d", "2w", "8mo" |
| | `_district_competitor_count()` — Other candidates in same district |
| **State** | `load_state()` / `save_state()` — state.json persistence |
| **Sheets** | `sync_to_google_sheets()` — Optional Google Sheets sync |
| **CLI** | `send_test_emails()` — `--test-email` mode with mock data |
| | `main()` — Full workflow orchestrator |

**Graceful degradation:** `party_detector`, `sheets_sync`, and `config` are all try/except imports. Script works without any of them.

---

### `src/config.py` — Configuration (368 lines)

Environment variables, constants, Google credentials loader.

| Function | Purpose |
|----------|---------|
| `get_google_credentials()` | Load service account from base64/file/JSON |
| `load_incumbents()` | Load incumbents.json (local or GitHub Pages) |
| `parse_district_from_office(office)` | "H091" or "S015" from office string |
| `is_house_district(office)` | Boolean check |

**Constants:** API keys, Google Sheet ID, confidence levels, fuzzy match threshold (85), party website URLs.

---

### `src/party_detector.py` — Party Detection (401 lines)

Multi-source party affiliation detection. Confidence tiers: HIGH → MEDIUM → LOW.

| Function | Purpose |
|----------|---------|
| `detect_party(name, office)` | Incumbent match → Firecrawl web search → aggregate |
| `detect_party_batch(candidates)` | Batch detection for multiple candidates |
| `needs_manual_review(result)` | True if LOW or UNKNOWN confidence |

**Sources:** Incumbent DB (HIGH), SCDP/SCGOP websites (HIGH), Ballotpedia (MEDIUM), other web (LOW).

**Depends on:** `config`, `incumbent_matcher`, `firecrawl-py` (optional).

---

### `src/incumbent_matcher.py` — Name Matching (344 lines)

Fuzzy name matching against incumbents.json.

| Function | Purpose |
|----------|---------|
| `match_against_incumbents(name, office)` | Match candidate to district incumbent |
| `fuzzy_name_match(name1, name2)` | Score 0-100 (fuzzywuzzy or Jaccard fallback) |
| `normalize_name(name)` | Strip titles, initials, nicknames |
| `is_candidate_incumbent(name, office)` | Quick boolean check |

**Threshold:** Score >= 85 = HIGH confidence match.

---

### `src/sheets_sync.py` — Google Sheets (250 lines)

Optional Google Sheets integration. Hangs on import if credentials unavailable — do not import locally without credentials.

| Method | Purpose |
|--------|---------|
| `SheetsSync.connect()` | Authenticate with service account |
| `SheetsSync.add_candidate()` | Add to Candidates tab |
| `SheetsSync.log_sync_event()` | Add to Sync Log tab |

---

### `src/backfill.py` — Historical Data Loader (336 lines)

**Standalone CLI tool** — not imported by monitor.py.

```bash
python src/backfill.py --dry-run          # Preview
python src/backfill.py --init-sheets      # Initialize Sheet structure
python src/backfill.py                    # Run backfill
```

---

### `src/sources/` — Party Detection Sources

| File | Purpose |
|------|---------|
| `ballotpedia.py` | Ballotpedia candidate search (MEDIUM confidence) |
| `party_sites.py` | SCDP/SCGOP website search (HIGH confidence) |
| `social_media.py` | Social media party signals (MEDIUM confidence) |

---

## Dependency Graph

```
monitor.py ──┬── config.py (optional)
             ├── party_detector.py (optional) ──┬── config.py
             │                                   ├── incumbent_matcher.py ── config.py
             │                                   └── sources/*.py
             └── sheets_sync.py (optional) ────── config.py

backfill.py ── config.py, sheets_sync.py, party_detector.py (standalone CLI)
```

All support modules degrade gracefully if unavailable.

---

## State File (`state.json`)

```json
{
  "seen_report_ids": ["414669", ...],        // 74 tracked IDs
  "last_checked": "2026-03-18T...",          // Last scrape timestamp
  "reports_with_metadata": { ... },          // ~26 current candidates
  "historical_2025": { ... }                 // ~36 historical entries
}
```

Auto-committed by GitHub Actions after each run.

---

## Dependencies (`requirements.txt`)

| Package | Purpose |
|---------|---------|
| `playwright` | Headless browser scraping |
| `requests` | Resend/SendGrid API calls |
| `gspread` + `google-auth` | Google Sheets sync |
| `firecrawl-py` | Web scraping for party detection |
| `fuzzywuzzy` + `python-Levenshtein` | Fuzzy name matching |

---

## Workflow (`.github/workflows/monitor.yml`)

**Trigger:** `cron: '0 0 * * *'` (midnight UTC = 7 PM EST) + manual dispatch

**Steps:** Checkout → Python 3.11 → Install deps + Playwright → Setup Google creds → Run monitor.py → Commit state.json

**Secrets:** `RESEND_API_KEY`, `NOTIFICATION_EMAIL`, `FROM_EMAIL`, `GOOGLE_SHEETS_CREDENTIALS`, `GOOGLE_SHEET_ID`, `FIRECRAWL_API_KEY`

---

## Documentation

| File | Content |
|------|---------|
| `CLAUDE.md` | AI assistant context — architecture, gotchas, pipeline, branding |
| `README.md` | Setup instructions, file structure, troubleshooting |
| `docs/SC-Ethics-Monitor-Overview.md` | Stakeholder-facing overview |
| `claudedocs/SCRAPING-WORKFLOW.md` | Playwright scraper deep-dive |
| `sc-ethics-initial-report-spec.md` | Original spec (validated Jan 2026) |

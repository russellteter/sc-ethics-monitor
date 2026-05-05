"""CLI: ``python -m src.finance`` — full scrape run.

Wires the modules in :mod:`src.finance` together for a production run:

1. Load the Dem House roster from the authoritative sc-filing-coverage-map
   ``candidates.json`` (party-tagged, kept fresh by that project's pipeline).
2. For each candidate: resolve URL params (cache → state → Playwright search),
   find the latest Quarterly report, fetch its detail page, parse the three
   numbers.
3. Write ``data/house_finance.json`` and update ``data/personId_cache.json``.

Exit codes:
    0 success
    2 scrape failure rate exceeded ``--max-failure-rate`` (default 0.2)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone

from src.finance import config
from src.finance.builder import ScrapeFailureRateExceeded, build_artifact

# Master Tracker spreadsheet ID (see CLAUDE.md "Gotchas").
MASTER_TRACKER_SHEET_ID = "1_SztBdJyl4FoPrtPiduKvrrnttisZDAJRLiHeoyFxLY"
from src.finance.coverage_roster import (
    fetch_coverage_candidates,
    load_dem_house_roster_from_coverage,
)
from src.finance.fetcher import fetch_html, make_playwright_fetcher
from src.finance.parser import parse_report_detail
from src.finance.playwright_ops import fetch_reports_list, search_personId
from src.finance.resolver import (
    UrlParams,
    find_latest_quarterly_from_rows,
    resolve_with_fallback,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m src.finance",
        description="Scrape SC House Dem campaign-finance data from ethicsfiling.sc.gov",
    )
    p.add_argument(
        "--cycle",
        default="2026",
        help="Election cycle label (default: 2026)",
    )
    p.add_argument(
        "--max-failure-rate",
        type=float,
        default=0.2,
        help="Abort with non-zero exit if more than this share of candidates fail (default: 0.2)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Load the roster and print its size, then exit without scraping.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    log = logging.getLogger("finance.main")

    log.info("loading roster from sc-filing-coverage-map …")
    try:
        coverage_data = fetch_coverage_candidates(cache_path=config.COVERAGE_CACHE_PATH)
    except Exception as e:
        log.error("failed to load coverage candidates: %s", e)
        print("roster size: 0 Dem House candidates (coverage source unreachable)")
        return 0 if args.dry_run else 2
    candidates = load_dem_house_roster_from_coverage(coverage_data)
    log.info("roster size: %d Dem House candidates (source: coverage-map %s)",
             len(candidates), coverage_data.get("lastUpdated", "?"))
    print(f"roster size: {len(candidates)} Dem House candidates")

    if args.dry_run:
        return 0

    if len(candidates) < 100:
        log.warning(
            "roster suspiciously small (%d); expected ~160 Dem House candidates. "
            "Check coverage-map freshness.",
            len(candidates),
        )
    if not candidates:
        log.error("no candidates to scrape — aborting")
        return 2

    pw_fetch = make_playwright_fetcher()

    # Performance: skip the Playwright "search by name" step. With 162
    # candidates and the search taking ~10s each, that's 25+ minutes wasted
    # on candidates who haven't filed any Ethics report (the majority). Only
    # candidates already in our resolver cache or in the Ethics state's
    # reports_with_metadata get resolved; the rest are marked `not_filed`,
    # which is the correct status anyway. To recover individual missing-
    # personId records, run the legacy monitor.py first to populate the
    # Ethics state.json with newly filed Initial Reports.
    def _no_search(_name: str, _district: int):
        return None

    def resolve(cid: str, name: str, district: int):
        return resolve_with_fallback(
            candidate_id=cid,
            candidate_name=name,
            district=district,
            cache_path=config.PERSONID_CACHE_PATH,
            ethics_state_path=config.ETHICS_STATE_PATH,
            playwright_search=_no_search,
        )

    def find_latest(params: UrlParams):
        rows = fetch_reports_list(params)
        return find_latest_quarterly_from_rows(rows)

    def fetch_and_parse(url: str):
        html = fetch_html(
            url,
            validator=lambda t: any(s in t.lower() for s in ("campaign funds", "cash contributions")),
            playwright_fetch=pw_fetch,
        )
        return parse_report_detail(html)

    log.info("building artifact …")
    try:
        build_artifact(
            candidates=candidates,
            out_path=config.HOUSE_FINANCE_PATH,
            cache_path=config.PERSONID_CACHE_PATH,
            resolve_fn=resolve,
            find_latest_fn=find_latest,
            fetch_and_parse_fn=fetch_and_parse,
            cycle=args.cycle,
            now_iso=_now_iso(),
            max_failure_rate=args.max_failure_rate,
        )
    except ScrapeFailureRateExceeded as e:
        log.error("aborting: %s", e)
        return 2

    # Best-effort Google Sheets sync. Never blocks the artifact write.
    # Lazy import: avoids loading gspread/google-auth on systems without them
    # and keeps the legacy `sheets_sync` import-hang gotcha (see CLAUDE.md)
    # contained to this branch.
    try:
        with open(config.HOUSE_FINANCE_PATH, "r") as f:
            artifact = json.load(f)
        sheet_id = os.getenv("MASTER_TRACKER_SHEET_ID", MASTER_TRACKER_SHEET_ID)
        from src.finance.sheets import sync_house_finance_to_sheet
        ok = sync_house_finance_to_sheet(artifact, sheet_id)
        if ok:
            log.info("synced house_finance to Google Sheet '%s'", sheet_id)
        else:
            log.info("Google Sheets sync skipped or failed (non-fatal)")
    except Exception as e:  # noqa: BLE001 — never block on sync errors
        log.warning("Google Sheets sync raised unexpectedly (non-fatal): %s", e)

    log.info("done: %s", config.HOUSE_FINANCE_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())

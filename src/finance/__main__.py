"""CLI: ``python -m src.finance`` — full scrape run.

Wires the modules in :mod:`src.finance` together for a production run:

1. Load the Dem House roster from VREMS state + party overrides.
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
import logging
import sys
from datetime import datetime, timezone

from src.finance import config
from src.finance.builder import ScrapeFailureRateExceeded, build_artifact
from src.finance.fetcher import fetch_html, make_playwright_fetcher
from src.finance.parser import parse_report_detail
from src.finance.party_loader import load_party_overrides
from src.finance.playwright_ops import fetch_reports_list, search_personId
from src.finance.resolver import (
    UrlParams,
    find_latest_quarterly_from_rows,
    resolve_with_fallback,
)
from src.finance.roster import load_dem_house_roster


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

    log.info("loading roster …")
    party_overrides = load_party_overrides()
    if not config.VREMS_STATE_PATH.exists():
        log.warning(
            "VREMS state file not found at %s — cannot build roster",
            config.VREMS_STATE_PATH,
        )
        print(f"roster size: 0 Dem House candidates (VREMS state missing at {config.VREMS_STATE_PATH})")
        return 0 if args.dry_run else 2
    candidates = load_dem_house_roster(config.VREMS_STATE_PATH, party_overrides)
    log.info("roster size: %d Dem House candidates", len(candidates))
    print(f"roster size: {len(candidates)} Dem House candidates")

    if args.dry_run:
        return 0

    if len(candidates) < 30:
        log.warning(
            "roster suspiciously small (%d); check VREMS state freshness at %s",
            len(candidates),
            config.VREMS_STATE_PATH,
        )
    if not candidates:
        log.error("no candidates to scrape — aborting")
        return 2

    pw_fetch = make_playwright_fetcher()

    def resolve(cid: str, name: str, district: int):
        return resolve_with_fallback(
            candidate_id=cid,
            candidate_name=name,
            district=district,
            cache_path=config.PERSONID_CACHE_PATH,
            ethics_state_path=config.ETHICS_STATE_PATH,
            playwright_search=search_personId,
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

    log.info("done: %s", config.HOUSE_FINANCE_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())

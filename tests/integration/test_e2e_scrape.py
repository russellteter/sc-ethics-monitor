"""End-to-end live scrape test.

Hits the real SC Ethics Commission site for one known candidate (Heather
Bauer's Q1 2026 quarterly disclosure) and verifies the parser extracts
non-zero values that satisfy the basic accounting identity.

Skipped unless RUN_LIVE_SCRAPE=1 is set. Non-blocking in CI.
"""

from __future__ import annotations

import os

import pytest

from src.finance.fetcher import fetch_html, make_playwright_fetcher
from src.finance.parser import parse_report_detail


LIVE_SCRAPE_ENABLED = os.environ.get("RUN_LIVE_SCRAPE") == "1"


@pytest.mark.skipif(not LIVE_SCRAPE_ENABLED, reason="live scrape opt-in")
def test_heather_bauer_live() -> None:
    """Scrape Bauer's known Q1 2026 report end-to-end and validate the numbers."""
    url = (
        "https://ethicsfiling.sc.gov/public/candidates-public-officials/"
        "person/campaign-disclosure-reports/report-detail"
        "?personId=45921&seiId=51547&officeId=71866&reportId=418208"
    )

    def _validator(text: str) -> bool:
        # The report-detail page should contain at least one of the disclosure
        # vocabulary words once it has rendered.
        lower = text.lower()
        return any(token in lower for token in ("receipts", "cash", "disclosure"))

    html = fetch_html(
        url,
        validator=_validator,
        playwright_fetch=make_playwright_fetcher(),
    )

    nums = parse_report_detail(html)

    # Sanity-check assertions; values may drift if amendments are filed but
    # the relationships should hold for any quarterly report.
    assert nums.cash_on_hand > 0, "cash_on_hand should be positive"
    assert nums.total_raised > 0, "total_raised should be positive"
    assert nums.period_raised >= 0, "period_raised must be non-negative"
    assert nums.total_raised >= nums.period_raised, (
        "total_raised should be >= period_raised "
        f"(got total={nums.total_raised}, period={nums.period_raised})"
    )

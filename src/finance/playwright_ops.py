"""Playwright helpers for personId search + reports list page parsing.

These functions wrap a headless browser session against ethicsfiling.sc.gov.
They're imported but not exercised by the unit-test suite — only the pure
``_normalize_row`` helper is unit-tested. End-to-end behaviour is verified by
the integration tests (owned by the Testing agent).
"""
from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import parse_qs, urlparse

from src.finance.config import (
    ETHICS_BASE,
    ETHICS_REPORTS_LIST,
    REQUEST_TIMEOUT_SEC,
    USER_AGENT,
)
from src.finance.resolver import UrlParams

logger = logging.getLogger(__name__)


def search_personId(name: str, district: int) -> Optional[UrlParams]:
    """Search the Ethics public site by candidate name; return :class:`UrlParams` if found.

    The page renders a list of candidate links with ``personId``, ``seiId`` and
    ``officeId`` query-string parameters. We pick the first link whose
    surrounding row references the expected ``district``.
    """
    from playwright.sync_api import sync_playwright  # local import — avoids hard dep

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(user_agent=USER_AGENT)
            page.goto(
                f"{ETHICS_BASE}/public/candidates-public-officials",
                wait_until="networkidle",
                timeout=REQUEST_TIMEOUT_SEC * 1000,
            )
            page.fill(
                "input[type=search], input[name='q'], input[placeholder*='earch' i]",
                name,
            )
            page.keyboard.press("Enter")
            page.wait_for_load_state("networkidle", timeout=REQUEST_TIMEOUT_SEC * 1000)
            anchors = page.query_selector_all("a[href*='personId=']")
            page_html = page.content().lower()
            for a in anchors:
                href = a.get_attribute("href") or ""
                text = (a.text_content() or "").lower()
                # Loose district sanity check: either the link text or the
                # whole rendered page must mention the district number.
                haystack = text or page_html
                if str(district) not in haystack:
                    continue
                qs = parse_qs(urlparse(href).query)
                pid = qs.get("personId", [None])[0]
                sid = qs.get("seiId", [None])[0]
                oid = qs.get("officeId", [None])[0]
                if pid and sid and oid:
                    return UrlParams(personId=pid, seiId=sid, officeId=oid)
            return None
        except Exception as e:  # noqa: BLE001
            logger.warning("search_personId failed for %s: %s", name, e)
            return None
        finally:
            browser.close()


def fetch_reports_list(params: UrlParams) -> list[dict]:
    """Open a candidate's reports-list page and return parsed rows."""
    from playwright.sync_api import sync_playwright

    url = (
        f"{ETHICS_REPORTS_LIST}"
        f"?personId={params.personId}&seiId={params.seiId}&officeId={params.officeId}"
    )
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(user_agent=USER_AGENT)
            page.goto(url, wait_until="networkidle", timeout=REQUEST_TIMEOUT_SEC * 1000)
            rows = page.evaluate(
                """() => {
                    const out = [];
                    document.querySelectorAll('a[href*="reportId="]').forEach(a => {
                        const tr = a.closest('tr');
                        if (!tr) return;
                        const cells = Array.from(tr.querySelectorAll('td'))
                            .map(td => td.innerText.trim());
                        const m = a.getAttribute('href').match(/reportId=(\\d+)/);
                        out.push({
                            reportId: m ? m[1] : null,
                            url: new URL(a.getAttribute('href'), location.href).toString(),
                            cells
                        });
                    });
                    return out;
                }"""
            )
            return [_normalize_row(r) for r in rows]
        finally:
            browser.close()


def _normalize_row(raw: dict) -> dict:
    """Translate raw cell text into the row schema consumed by :mod:`builder`.

    Returned dict keys: ``reportId``, ``url``, ``report_type``, ``filed_date``,
    ``period_label``, ``is_amended``.
    """
    cells = raw.get("cells", [])
    text = " | ".join(cells).lower()

    is_amended = "amend" in text

    if "quarterly" in text:
        report_type = "Quarterly"
    elif "initial" in text:
        report_type = "Initial"
    elif "pre-election" in text or "pre election" in text:
        report_type = "Pre-Election"
    elif "final" in text:
        report_type = "Final"
    else:
        report_type = "Other"

    filed_date = ""
    period_label = ""
    for c in cells:
        if c and c[0].isdigit() and "/" in c and not filed_date:
            filed_date = c
        # Period labels look like "Q1 2026", "Q4 2025"
        if c and c[0].lower() == "q" and any(d.isdigit() for d in c) and not period_label:
            period_label = c

    return {
        "reportId": raw.get("reportId"),
        "url": raw.get("url"),
        "report_type": report_type,
        "filed_date": filed_date,
        "period_label": period_label,
        "is_amended": is_amended,
    }

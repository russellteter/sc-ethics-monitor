"""HTTP-first fetcher with optional Playwright fallback and exponential-backoff retries.

The Ethics report-detail pages are Angular SPAs: a plain HTTP GET returns the
shell, not the data. We try ``httpx`` first (cheap, fast) and only fall back
to Playwright when (a) the response doesn't pass the caller-supplied
``validator``, or (b) all HTTP retries are exhausted and a fallback callable
is provided.
"""
from __future__ import annotations

import logging
import time
from typing import Callable, Optional

import httpx

from src.finance.config import (
    INTER_REQUEST_DELAY_SEC,
    REQUEST_TIMEOUT_SEC,
    RETRY_BACKOFF_BASE_SEC,
    RETRY_MAX,
    USER_AGENT,
)

logger = logging.getLogger(__name__)


class FetchError(Exception):
    """Raised when both HTTP and Playwright (if any) fail to produce a usable response."""


PlaywrightFetch = Callable[[str], str]
Validator = Callable[[str], bool]


def fetch_html(
    url: str,
    *,
    validator: Optional[Validator] = None,
    playwright_fetch: Optional[PlaywrightFetch] = None,
) -> str:
    """Fetch ``url`` over HTTP with retries; fall back to Playwright if needed.

    Args:
        url: target URL.
        validator: optional ``(html) -> bool``. If supplied, a successful HTTP
            response whose body fails the validator is treated as "not the
            data we wanted" and we either fall back to Playwright (if given)
            or raise ``FetchError``.
        playwright_fetch: optional ``(url) -> html`` invoked when HTTP fails
            outright or when the validator rejects the HTTP body.

    Raises:
        FetchError: when no usable HTML can be obtained.
    """
    last_exc: Optional[Exception] = None
    for attempt in range(RETRY_MAX):
        if attempt == 0:
            time.sleep(INTER_REQUEST_DELAY_SEC)
        try:
            r = httpx.get(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
                timeout=REQUEST_TIMEOUT_SEC,
                follow_redirects=True,
            )
            r.raise_for_status()
            html = r.text
            if validator and not validator(html):
                if playwright_fetch:
                    logger.info("validator rejected HTTP body for %s; trying playwright", url)
                    return _try_playwright(playwright_fetch, url, last_exc)
                raise FetchError(f"validator rejected response body for {url}")
            return html
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            last_exc = e
            sleep_sec = RETRY_BACKOFF_BASE_SEC * (2**attempt)
            logger.debug("attempt %d failed for %s: %s; sleep %.1fs", attempt + 1, url, e, sleep_sec)
            time.sleep(sleep_sec)
    if playwright_fetch:
        return _try_playwright(playwright_fetch, url, last_exc)
    raise FetchError(f"http retries exhausted for {url}: {last_exc}") from last_exc


def _try_playwright(
    playwright_fetch: PlaywrightFetch,
    url: str,
    http_error: Optional[Exception],
) -> str:
    try:
        return playwright_fetch(url)
    except Exception as pe:
        msg = f"playwright fallback failed for {url}: {pe}"
        if http_error is not None:
            msg = f"http error: {http_error}; {msg}"
        raise FetchError(msg) from pe


def make_playwright_fetcher() -> PlaywrightFetch:
    """Return a callable that fetches a URL via headless Chromium and returns rendered HTML."""
    from playwright.sync_api import sync_playwright

    def _fetch(url: str) -> str:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page(user_agent=USER_AGENT)
                page.goto(url, wait_until="networkidle", timeout=REQUEST_TIMEOUT_SEC * 1000)
                return page.content()
            finally:
                browser.close()

    return _fetch

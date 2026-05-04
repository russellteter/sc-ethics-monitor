"""Parse SC Ethics report-detail HTML to extract three financial numbers.

The report-detail page renders an Angular Kendo grid with **3-column rows**:
``Label | This Period | Election Cycle Total``.  See ``tests/finance/fixtures/
PARSER_NOTES.md`` for the verified structure.

Three target fields:

=================== ============================================== ============
Field               Source row                                     Column
=================== ============================================== ============
``period_raised``   First "Total" row in the receipts section      Col 1 (period)
``total_raised``    Same row                                       Col 2 (aggregate)
``cash_on_hand``    "Campaign Funds" row                           Col 2 (Ending)
=================== ============================================== ============

The receipts section is bounded by a row whose label contains "Cash Contributions"
(start) and a subsequent row whose label is "Expenditures" (end). The first
"Total" row encountered between those anchors is the receipts total. Anchoring
this way avoids confusing the receipts total with the expenditures total, both
of which are labelled simply "Total".
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class ReportNumbers:
    period_raised: float
    total_raised: float
    cash_on_hand: float


class ParseError(Exception):
    """Raised when the expected fields can't be extracted from the HTML."""


# Matches ``$1,234.56``, ``1,234.56``, ``$-1,234.56``, etc. The leading sign
# is captured so we can detect negatives and refuse them downstream.
_NUMBER_RE = re.compile(r"(-?)\$?\s*-?\s*([\d,]+\.\d{2})")


def parse_report_detail(html: str) -> ReportNumbers:
    """Extract ``ReportNumbers`` from a rendered report-detail HTML document.

    Raises:
        ParseError: when the receipts ``Total`` row or the ``Campaign Funds``
            row can't be located, or any extracted amount is negative.
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = _extract_rows(soup)
    if not rows:
        raise ParseError("no table rows found")

    period_raised, total_raised = _extract_receipts_total(rows)
    cash_on_hand = _extract_campaign_funds(rows)

    for name, value in (
        ("period_raised", period_raised),
        ("total_raised", total_raised),
        ("cash_on_hand", cash_on_hand),
    ):
        if value < 0:
            raise ParseError(f"negative value for {name}: {value}")

    return ReportNumbers(
        period_raised=period_raised,
        total_raised=total_raised,
        cash_on_hand=cash_on_hand,
    )


def _extract_rows(soup: BeautifulSoup) -> list[list[str]]:
    """Return cell-text lists for every ``<tr>`` that has at least one ``<td>``/``<th>``."""
    out: list[list[str]] = []
    for tr in soup.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue
        texts = [c.get_text(" ", strip=True) for c in cells]
        if any(texts):
            out.append(texts)
    return out


def _extract_receipts_total(rows: list[list[str]]) -> tuple[float, float]:
    """Find ``period_raised`` + ``total_raised`` from the receipts ``Total`` row.

    The receipts section starts at the first row whose first cell contains
    "Cash Contributions" and ends at the next row whose first cell starts
    with "Expenditures" (or "Expenditure", which is the section header label
    on the live site). Within that span, the first row whose label is exactly
    "Total" carries the period and aggregate sums.
    """
    in_receipts = False
    for row in rows:
        label = row[0].strip()
        label_lower = label.lower()
        if not in_receipts:
            if "cash contributions" in label_lower:
                in_receipts = True
            continue
        # We're inside the receipts section.
        if label_lower.startswith("expenditure"):
            # Hit the end-anchor without seeing a Total row.
            break
        if label_lower == "total":
            if len(row) < 3:
                raise ParseError(
                    f"receipts Total row has only {len(row)} cells; need 3"
                )
            period = _parse_amount(row[1])
            aggregate = _parse_amount(row[2])
            if period is None or aggregate is None:
                raise ParseError(f"cannot parse receipts Total values: {row!r}")
            return period, aggregate
    raise ParseError("receipts Total row not found")


def _extract_campaign_funds(rows: list[list[str]]) -> float:
    """Find the ``Campaign Funds`` row and return its Ending Balance (column 2)."""
    for row in rows:
        if row[0].strip().lower() == "campaign funds":
            if len(row) < 3:
                raise ParseError(
                    f"Campaign Funds row has only {len(row)} cells; need 3"
                )
            ending = _parse_amount(row[2])
            if ending is None:
                raise ParseError(f"cannot parse Campaign Funds Ending Balance: {row!r}")
            return ending
    raise ParseError("Campaign Funds row not found")


def _parse_amount(text: str) -> Optional[float]:
    """Parse a currency-formatted amount, preserving sign.

    Returns ``None`` when the text contains no number we can extract.
    """
    if text is None:
        return None
    raw = text.strip()
    if not raw:
        return None
    # Detect a leading minus (possibly between $ and digits).
    is_negative = bool(re.search(r"-\s*\$?\s*\d", raw)) or raw.startswith("-")
    m = _NUMBER_RE.search(raw)
    if not m:
        return None
    value = float(m.group(2).replace(",", ""))
    return -value if is_negative else value

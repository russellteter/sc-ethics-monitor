"""Resolve candidate name → Ethics URL params via cache → state → playwright.

The Ethics report-detail URL needs three IDs: ``personId``, ``seiId``, ``officeId``.
This module looks them up in three places, in order of cost:

1. ``data/personId_cache.json`` — keyed by our internal ``candidate_id``.
2. The local Ethics ``state.json`` — keyed by candidate name, with a district sanity
   check.
3. A Playwright search of the live Ethics website (caller-supplied function).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import parse_qs, urlparse


@dataclass(frozen=True)
class UrlParams:
    """Three IDs that identify a candidate's report-detail URL on ethicsfiling.sc.gov."""

    personId: str
    seiId: str
    officeId: str


PlaywrightSearch = Callable[[str, int], Optional[UrlParams]]


def _read_json(path: Path) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    txt = p.read_text() or "{}"
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        return {}


def resolve_from_cache(cache_path: Path, candidate_id: str) -> Optional[UrlParams]:
    """Cache hit returns :class:`UrlParams`; miss or unreadable file returns ``None``."""
    data = _read_json(cache_path)
    entry = data.get(candidate_id)
    if not entry:
        return None
    try:
        return UrlParams(
            personId=str(entry["personId"]),
            seiId=str(entry["seiId"]),
            officeId=str(entry["officeId"]),
        )
    except KeyError:
        return None


def resolve_from_ethics_state(
    ethics_state_path: Path,
    candidate_name: str,
    district: int,
) -> Optional[UrlParams]:
    """Search the local Ethics state for a matching candidate.

    Names come in two formats: roster (``"First [Middle] Last"``) vs. Ethics state
    (``"Last, First [Middle]"``). We narrow to the right district first, then try
    a first+last match, falling back to last-name-only within the district. Both
    sides are reduced to ``(first, last)`` token pairs so middle names/initials
    don't break matching.
    """
    data = _read_json(ethics_state_path)
    raw = data.get("reports_with_metadata", [])
    # Accept both shapes: list-of-dicts (test fixture) and dict-of-dicts (live state).
    if isinstance(raw, dict):
        reports = list(raw.values())
    else:
        reports = raw

    target_first, target_last = _first_last(candidate_name)
    if not target_last:
        return None

    in_district = []
    for r in reports:
        if not isinstance(r, dict):
            continue
        if not _district_matches(r.get("office", "") or "", district):
            continue
        in_district.append(r)

    # First pass: exact (first, last) match.
    for r in in_district:
        ethics_name = r.get("candidate") or r.get("candidate_name") or ""
        e_first, e_last = _first_last_from_lastfirst(ethics_name)
        if e_first == target_first and e_last == target_last:
            params = _extract_url_params(r)
            if params is not None:
                return params

    # Fallback: same district + same last name. Common when the candidate goes
    # by a middle name on Ethics filings (``Linvill, Claiborne``) while the
    # roster carries the full legal name (``Caroline Claiborne Linvill``).
    last_matches = [
        r for r in in_district
        if _first_last_from_lastfirst(r.get("candidate") or r.get("candidate_name") or "")[1] == target_last
    ]
    if len(last_matches) == 1:
        return _extract_url_params(last_matches[0])
    return None


def _district_matches(office: str, district: int) -> bool:
    """Match the exact district number, not a substring (e.g. ``3`` shouldn't hit ``District 30``)."""
    m = re.search(r"District\s+(\d+)", office or "")
    return bool(m) and int(m.group(1)) == district


def _first_last(name: str) -> tuple[str, str]:
    """``"Brittany June Lynch"`` → ``("brittany", "lynch")``. Strips middles."""
    tokens = (name or "").lower().split()
    if not tokens:
        return ("", "")
    if len(tokens) == 1:
        return (tokens[0], tokens[0])
    return (tokens[0], tokens[-1])


def _first_last_from_lastfirst(ethics_name: str) -> tuple[str, str]:
    """``"Bauer, Heather M"`` → ``("heather", "bauer")``."""
    if "," in ethics_name:
        last, first = [s.strip() for s in ethics_name.split(",", 1)]
        first_word = first.split()[0] if first else ""
        return (first_word.lower(), last.lower())
    return _first_last(ethics_name)


def _extract_url_params(report: dict) -> Optional[UrlParams]:
    """Read personId/seiId/officeId from explicit fields, else parse from ``url``."""
    pid = report.get("personId")
    sid = report.get("seiId")
    oid = report.get("officeId")
    if pid and sid and oid:
        return UrlParams(personId=str(pid), seiId=str(sid), officeId=str(oid))
    url = report.get("url") or ""
    if not url:
        return None
    qs = parse_qs(urlparse(url).query)
    try:
        return UrlParams(
            personId=qs["personId"][0],
            seiId=qs["seiId"][0],
            officeId=qs["officeId"][0],
        )
    except (KeyError, IndexError):
        return None


def _normalize_lastfirst(ethics_name: str) -> str:
    """``"Bauer, Heather M"`` → ``"heather bauer"``."""
    if "," in ethics_name:
        last, first = [s.strip() for s in ethics_name.split(",", 1)]
        first_word = first.split()[0] if first else ""
        return f"{first_word} {last}".lower().strip()
    return ethics_name.lower().strip()


def resolve_with_fallback(
    *,
    candidate_id: str,
    candidate_name: str,
    district: int,
    cache_path: Path,
    ethics_state_path: Path,
    playwright_search: PlaywrightSearch,
) -> Optional[UrlParams]:
    """Try cache → ethics-state → playwright in order, returning the first hit."""
    cached = resolve_from_cache(cache_path, candidate_id)
    if cached is not None:
        return cached
    state_hit = resolve_from_ethics_state(ethics_state_path, candidate_name, district)
    if state_hit is not None:
        return state_hit
    return playwright_search(candidate_name, district)


def find_latest_quarterly_from_rows(rows: list[dict]) -> Optional[dict]:
    """Pick the most recent ``Quarterly`` report row.

    Primary sort key is the period the report covers (year + quarter, parsed
    from ``period_label`` like ``"Quarter 1, 2026 Report"``). Filed date is the
    tiebreaker. When two quarterlies share both, the amended one wins. Falling
    back to ``filed_date`` alone is unreliable because the column on the live
    Ethics page often shows an "updated" date that doesn't agree with the
    period — and lexicographic sort on ``MM/DD/YYYY`` is wrong anyway.
    """
    quarterly = [r for r in rows if r.get("report_type") == "Quarterly"]
    if not quarterly:
        return None
    quarterly.sort(
        key=lambda r: (
            _period_sort_key(r.get("period_label", "")),
            _filed_date_sort_key(r.get("filed_date", "")),
            bool(r.get("is_amended")),
        ),
        reverse=True,
    )
    return quarterly[0]


def _period_sort_key(label: str) -> tuple[int, int]:
    """``"Quarter 2, 2026 Report"`` → ``(2026, 2)``. Unparseable → ``(0, 0)``."""
    if not label:
        return (0, 0)
    quarter_match = re.search(r"quarter\s*(\d)", label, re.IGNORECASE)
    year_match = re.search(r"(20\d{2})", label)
    q = int(quarter_match.group(1)) if quarter_match else 0
    y = int(year_match.group(1)) if year_match else 0
    return (y, q)


def _filed_date_sort_key(filed: str) -> tuple[int, int, int]:
    """Parse ``MM/DD/YYYY`` or ``YYYY-MM-DD`` to a (Y, M, D) tuple. Unparseable → ``(0,0,0)``."""
    if not filed:
        return (0, 0, 0)
    s = filed.strip()
    # YYYY-MM-DD
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", s)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    # MM/DD/YYYY
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", s)
    if m:
        return (int(m.group(3)), int(m.group(1)), int(m.group(2)))
    return (0, 0, 0)


def update_cache(cache_path: Path, candidate_id: str, params: UrlParams) -> None:
    """Persist ``candidate_id → params`` to disk, merging with any existing entries."""
    data = _read_json(cache_path)
    data[candidate_id] = {
        "personId": params.personId,
        "seiId": params.seiId,
        "officeId": params.officeId,
    }
    p = Path(cache_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True))

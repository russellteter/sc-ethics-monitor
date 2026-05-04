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
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


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

    Names in Ethics state are formatted ``"Last, First M"``. We normalize before
    comparing, then sanity-check that the configured ``office`` string contains
    the expected ``district`` integer.
    """
    data = _read_json(ethics_state_path)
    raw = data.get("reports_with_metadata", [])
    # Accept both shapes: list-of-dicts (test fixture) and dict-of-dicts (live state).
    if isinstance(raw, dict):
        reports = list(raw.values())
    else:
        reports = raw
    target = candidate_name.lower().strip()
    for r in reports:
        if not isinstance(r, dict):
            continue
        ethics_name = r.get("candidate") or r.get("candidate_name") or ""
        normalized = _normalize_lastfirst(ethics_name)
        if normalized != target:
            continue
        office = r.get("office", "") or ""
        if str(district) not in office:
            continue
        try:
            return UrlParams(
                personId=str(r["personId"]),
                seiId=str(r["seiId"]),
                officeId=str(r["officeId"]),
            )
        except KeyError:
            continue
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

    Sort key is ``filed_date`` (lexicographic, since dates arrive as ``MM/DD/YYYY``
    or ``YYYY-MM-DD`` strings — both orderings agree for our use case). When two
    quarterlies share a filed_date, the amended one wins.
    """
    quarterly = [r for r in rows if r.get("report_type") == "Quarterly"]
    if not quarterly:
        return None
    quarterly.sort(
        key=lambda r: (r.get("filed_date", ""), bool(r.get("is_amended"))),
        reverse=True,
    )
    return quarterly[0]


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

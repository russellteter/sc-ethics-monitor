"""Orchestrate roster → resolve → fetch → parse → write JSON artifact.

The builder is the integration seam between the four single-purpose modules
(:mod:`roster`, :mod:`resolver`, :mod:`fetcher`, :mod:`parser`). It accepts
those modules' work as plain callables — that lets unit tests pass stubs and
keeps the dependency direction one-way.

Outputs ``data/house_finance.json`` with this shape:

.. code-block:: json

    {
      "schema_version": 1,
      "generated_at": "<iso-8601>",
      "cycle": "2026",
      "candidates": [{
        "id": "...", "name": "...", "district": 75, "party": "D",
        "personId": "...", "seiId": "...", "officeId": "...",
        "filing_status": "filed" | "not_filed" | "scrape_failed",
        "latest_report": {...} | null,
        "history": [],
        "last_error": null | "..."
      }, ...],
      "stats": { "total_dem_house": ..., "filed": ..., ... }
    }
"""
from __future__ import annotations

import json
import logging
import statistics
from pathlib import Path
from typing import Callable, Optional

from src.finance.config import SCHEMA_VERSION
from src.finance.parser import ReportNumbers
from src.finance.resolver import UrlParams, update_cache
from src.finance.roster import Candidate

logger = logging.getLogger(__name__)

ResolveFn = Callable[[str, str, int], Optional[UrlParams]]
FindLatestFn = Callable[[UrlParams], Optional[dict]]
FetchParseFn = Callable[[str], ReportNumbers]


class ScrapeFailureRateExceeded(Exception):
    """Raised when scrape failures exceed ``max_failure_rate``.

    The artifact is still written before raising so partial progress is preserved
    on disk; the exception signals the caller to exit non-zero.
    """


def build_artifact(
    *,
    candidates: list[Candidate],
    out_path: Path,
    cache_path: Path,
    resolve_fn: ResolveFn,
    find_latest_fn: FindLatestFn,
    fetch_and_parse_fn: FetchParseFn,
    cycle: str,
    now_iso: str,
    max_failure_rate: float = 0.5,
) -> None:
    """Build and write the house_finance.json artifact.

    For each candidate:

    1. ``resolve_fn`` → :class:`UrlParams` or ``None`` (skip).
    2. ``find_latest_fn`` → most recent quarterly meta dict, or ``None`` (mark
       ``not_filed``).
    3. ``fetch_and_parse_fn`` → :class:`ReportNumbers`. On failure, carry forward
       the prior ``latest_report`` if one exists in ``out_path``.

    Raises:
        ScrapeFailureRateExceeded: if more than ``max_failure_rate`` of
            candidates ended in ``scrape_failed``. The artifact is still written
            first so successes survive.
    """
    prior = _load_prior(out_path)
    out_candidates: list[dict] = []
    filed = 0
    not_filed = 0
    failed = 0
    for cand in candidates:
        record = _build_one(
            cand=cand,
            prior_record=prior.get(cand.id),
            cache_path=cache_path,
            resolve_fn=resolve_fn,
            find_latest_fn=find_latest_fn,
            fetch_and_parse_fn=fetch_and_parse_fn,
        )
        out_candidates.append(record)
        status = record["filing_status"]
        if status == "filed":
            filed += 1
        elif status == "not_filed":
            not_filed += 1
        else:
            failed += 1
    stats = _compute_stats(
        out_candidates,
        total=len(candidates),
        filed=filed,
        not_filed=not_filed,
        failed=failed,
    )
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso,
        "cycle": cycle,
        "candidates": out_candidates,
        "stats": stats,
    }
    _atomic_write(out_path, artifact)
    if candidates and (failed / len(candidates)) > max_failure_rate:
        raise ScrapeFailureRateExceeded(
            f"failure rate {failed}/{len(candidates)} exceeds {max_failure_rate}"
        )


def _build_one(
    *,
    cand: Candidate,
    prior_record: Optional[dict],
    cache_path: Path,
    resolve_fn: ResolveFn,
    find_latest_fn: FindLatestFn,
    fetch_and_parse_fn: FetchParseFn,
) -> dict:
    base: dict = {
        "id": cand.id,
        "name": cand.name,
        "district": cand.district,
        "party": cand.party,
        "personId": None,
        "seiId": None,
        "officeId": None,
        "filing_status": "not_filed",
        "latest_report": None,
        "history": [],
        "last_error": None,
    }
    params = resolve_fn(cand.id, cand.name, cand.district)
    if params is None:
        logger.info("no URL params for %s; marking not_filed", cand.name)
        return base
    base["personId"] = params.personId
    base["seiId"] = params.seiId
    base["officeId"] = params.officeId
    update_cache(cache_path, cand.id, params)

    latest_meta = find_latest_fn(params)
    if latest_meta is None:
        return base

    try:
        nums = fetch_and_parse_fn(latest_meta["url"])
    except Exception as e:  # noqa: BLE001 — any error → carry forward
        logger.warning("scrape failed for %s: %s", cand.name, e)
        base["filing_status"] = "scrape_failed"
        base["last_error"] = str(e)[:200]
        if prior_record and prior_record.get("latest_report"):
            base["latest_report"] = prior_record["latest_report"]
        return base

    base["filing_status"] = "filed"
    base["latest_report"] = {
        **latest_meta,
        "period_raised": nums.period_raised,
        "total_raised": nums.total_raised,
        "cash_on_hand": nums.cash_on_hand,
    }
    return base


def _compute_stats(
    records: list[dict],
    *,
    total: int,
    filed: int,
    not_filed: int,
    failed: int,
) -> dict:
    coh_records = [
        r
        for r in records
        if r["filing_status"] == "filed" and r.get("latest_report")
    ]
    coh = [r["latest_report"]["cash_on_hand"] for r in coh_records]
    period = [r["latest_report"]["period_raised"] for r in coh_records]
    if coh:
        median_coh = statistics.median(coh)
        top_record = max(coh_records, key=lambda r: r["latest_report"]["cash_on_hand"])
        top_coh = top_record["latest_report"]["cash_on_hand"]
        top_name = top_record["name"]
        top_dist = top_record["district"]
    else:
        median_coh = 0.0
        top_coh = 0.0
        top_name = None
        top_dist = None
    return {
        "total_dem_house": total,
        "filed": filed,
        "not_filed": not_filed,
        "scrape_failed": failed,
        "median_coh": round(median_coh, 2),
        "top_coh": round(top_coh, 2),
        "top_coh_candidate": top_name,
        "top_coh_district": top_dist,
        "total_q_raised": round(sum(period), 2),
        "total_coh_all": round(sum(coh), 2),
    }


def _load_prior(out_path: Path) -> dict:
    p = Path(out_path)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text() or "{}")
    except json.JSONDecodeError:
        return {}
    return {c["id"]: c for c in data.get("candidates", []) if "id" in c}


def _atomic_write(out_path: Path, data: dict) -> None:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=False))
    tmp.replace(p)

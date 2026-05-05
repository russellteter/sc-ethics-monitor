"""Authoritative Dem House roster from sc-filing-coverage-map.

The sibling project at https://github.com/russellteter/sc-filing-coverage-map
maintains a verified, party-tagged candidates.json updated daily. Reuse it as
the source of truth instead of running fragile party-detection web scraping
ourselves.
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

import httpx

from src.finance.config import (
    REQUEST_TIMEOUT_SEC,
    USER_AGENT,
)
from src.finance.roster import Candidate

logger = logging.getLogger(__name__)

DEFAULT_COVERAGE_URL = (
    "https://raw.githubusercontent.com/russellteter/"
    "sc-filing-coverage-map/main/public/data/candidates.json"
)

DEM_PARTY_LABEL = "Democratic"


def fetch_coverage_candidates(
    url: Optional[str] = None,
    cache_path: Optional[Path] = None,
) -> dict:
    """Fetch candidates.json from the coverage-map repo. On success, persist
    to cache_path for reproducibility. On HTTP failure, fall back to the
    cached copy if it exists.
    """
    url = url or os.environ.get("COVERAGE_CANDIDATES_URL") or DEFAULT_COVERAGE_URL
    try:
        r = httpx.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=REQUEST_TIMEOUT_SEC,
            follow_redirects=True,
        )
        r.raise_for_status()
        data = r.json()
        if cache_path is not None:
            p = Path(cache_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(data, indent=2))
        return data
    except Exception as e:
        logger.warning("coverage fetch failed: %s; trying cache at %s", e, cache_path)
        if cache_path and Path(cache_path).exists():
            return json.loads(Path(cache_path).read_text())
        raise


def load_dem_house_roster_from_coverage(data: dict) -> list[Candidate]:
    """Filter the coverage candidates.json to Democratic SC House candidates
    and convert to the project's Candidate dataclass.
    """
    out: list[Candidate] = []
    seen_ids: set[str] = set()
    house = data.get("house") or {}
    for dnum_key, district in house.items():
        try:
            dnum = int(dnum_key)
        except (TypeError, ValueError):
            continue
        for c in district.get("candidates", []) or []:
            if c.get("party") != DEM_PARTY_LABEL:
                continue
            if c.get("status") and c["status"] not in ("filed", "active", None):
                # Skip withdrawn / removed candidates
                continue
            name = (c.get("name") or "").strip()
            parts = name.split()
            if len(parts) < 2:
                continue
            first = parts[0]
            last = parts[-1]
            cid = re.sub(r"[^a-z0-9]+", "-",
                         f"{last.lower()}-{first.lower()}-{dnum}").strip("-")
            if cid in seen_ids:
                continue
            seen_ids.add(cid)
            out.append(Candidate(
                id=cid,
                name=name,
                district=dnum,
                party="D",
                office=f"SC House of Representatives District {dnum}",
            ))
    return out

"""Load Dem SC House roster from VREMS state.json.

The VREMS sibling repo emits a `state.json` whose `seen_candidate_keys` list contains
strings of the form ``last|first|office|district``. We:

1. Filter to "SC House of Representatives" via :data:`STATE_HOUSE_PATTERNS` from config.
2. Apply a caller-supplied party-override map (``last|first`` → ``D``/``R``/``I``/``O``)
   keeping only ``D`` entries.
3. Return a list of :class:`Candidate` value objects.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from src.finance.config import STATE_HOUSE_PATTERNS
from src.finance.party_detect import DetectorFn, detect_party_with_cache, make_real_detector


@dataclass(frozen=True)
class Candidate:
    """One Dem House candidate from the VREMS roster."""

    id: str
    name: str
    district: int
    party: str
    office: str

    @classmethod
    def from_vrems_key(cls, key: str, party: str) -> Optional["Candidate"]:
        """Parse a single ``last|first|office|district`` row.

        Returns ``None`` if the key is malformed or the office is not SC House.
        """
        parts = key.split("|")
        if len(parts) != 4:
            return None
        last, first, office, district_raw = parts
        if not _is_state_house(office):
            return None
        try:
            district = int(district_raw)
        except ValueError:
            return None
        last_clean = last.strip().title()
        first_clean = first.strip().title()
        if not last_clean or not first_clean:
            return None
        name = f"{first_clean} {last_clean}"
        cid = re.sub(
            r"[^a-z0-9]+",
            "-",
            f"{last_clean.lower()}-{first_clean.lower()}-{district}",
        ).strip("-")
        return cls(id=cid, name=name, district=district, party=party, office=office)


def _is_state_house(office: str) -> bool:
    return any(p.search(office) for p in STATE_HOUSE_PATTERNS)


def load_dem_house_roster(
    vrems_state_path: Path,
    party_overrides: Optional[dict[str, str]] = None,
) -> list[Candidate]:
    """Return the Dem-only SC House roster from a VREMS-style state file.

    Args:
        vrems_state_path: path to a JSON file with a ``seen_candidate_keys`` list.
        party_overrides: ``{"last|first": "D"|"R"|"I"|"O"}`` lookup; entries not in
            the map (or not ``"D"``) are skipped.
    """
    overrides = party_overrides or {}
    raw = json.loads(Path(vrems_state_path).read_text())
    keys: Iterable[str] = raw.get("seen_candidate_keys", [])
    out: list[Candidate] = []
    for key in keys:
        parts = key.split("|")
        if len(parts) < 2:
            continue
        last_first = f"{parts[0].strip().lower()}|{parts[1].strip().lower()}"
        party = overrides.get(last_first)
        if party != "D":
            continue
        cand = Candidate.from_vrems_key(key, party)
        if cand:
            out.append(cand)
    return out


def _detect_party(*, cache_path, cache_key, candidate_name, district, detector):
    """Indirection for monkey-patching in tests."""
    return detect_party_with_cache(
        cache_path=cache_path,
        cache_key=cache_key,
        candidate_name=candidate_name,
        district=district,
        detector=detector,
    )


def load_dem_house_roster_with_detection(
    *,
    vrems_state_path: Path,
    party_cache_path: Path,
    detector: Optional[DetectorFn] = None,
) -> list[Candidate]:
    """Return the Dem SC House roster, auto-detecting party for each candidate.

    Iterates the VREMS ``seen_candidate_keys`` list, filters to State House
    offices, and calls :func:`_detect_party` (which routes to the on-disk
    cache + legacy ``src/party_detector.py``) for each candidate. Only
    candidates the detector resolves to ``"D"`` are kept.

    Args:
        vrems_state_path: VREMS state.json (``{"seen_candidate_keys": [...]}``).
        party_cache_path: persistent cache file ``data/party_cache.json``.
        detector: optional injected :data:`DetectorFn`; defaults to
            :func:`make_real_detector` (Ballotpedia + incumbent matcher).
    """
    raw = json.loads(Path(vrems_state_path).read_text())
    keys: Iterable[str] = raw.get("seen_candidate_keys", [])
    if detector is None:
        detector = make_real_detector()
    out: list[Candidate] = []
    for key in keys:
        parts = key.split("|")
        if len(parts) != 4:
            continue
        last, first, office, district_raw = parts
        if not _is_state_house(office):
            continue
        try:
            district = int(district_raw)
        except ValueError:
            continue
        last_clean = last.strip().title()
        first_clean = first.strip().title()
        if not last_clean or not first_clean:
            continue
        name = f"{first_clean} {last_clean}"
        cache_key = f"{last_clean.lower()}|{first_clean.lower()}|{district}"
        party = _detect_party(
            cache_path=party_cache_path,
            cache_key=cache_key,
            candidate_name=name,
            district=district,
            detector=detector,
        )
        if party != "D":
            continue
        cid = re.sub(
            r"[^a-z0-9]+",
            "-",
            f"{last_clean.lower()}-{first_clean.lower()}-{district}",
        ).strip("-")
        out.append(
            Candidate(id=cid, name=name, district=district, party="D", office=office)
        )
    return out

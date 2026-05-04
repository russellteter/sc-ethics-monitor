"""Build a ``party_overrides`` dict from existing local data sources.

The dict shape is ``{"<last>|<first>": "D"|"R"|"I"|"O"}`` keyed by lowercase
last + first name, suitable for :func:`src.finance.roster.load_dem_house_roster`.

Primary signal: the local Ethics ``state.json`` file embeds ``detected_party``
or ``final_party`` per filing in ``reports_with_metadata`` when available.
Some historical state.json files use a dict-of-dicts shape keyed by reportId
with no party signal at all — in that case the loader returns an empty dict
and the caller must supply party overrides another way (e.g. a Google Sheet).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

from src.finance.config import ETHICS_STATE_PATH


def load_party_overrides(ethics_state_path: Optional[Path] = None) -> dict[str, str]:
    """Return ``{last|first → party-letter}`` from the local Ethics state file.

    Returns an empty dict if the file is missing, malformed, or contains no
    party-tagged records.
    """
    path = Path(ethics_state_path) if ethics_state_path else ETHICS_STATE_PATH
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text() or "{}")
    except json.JSONDecodeError:
        return {}
    rwm = data.get("reports_with_metadata", [])
    return _records_to_overrides(_iter_records(rwm))


def _iter_records(rwm) -> Iterable[dict]:
    """Yield record dicts from either a list (fixture shape) or dict-of-dicts (live shape)."""
    if isinstance(rwm, list):
        for r in rwm:
            if isinstance(r, dict):
                yield r
    elif isinstance(rwm, dict):
        for r in rwm.values():
            if isinstance(r, dict):
                yield r


def _records_to_overrides(records: Iterable[dict]) -> dict[str, str]:
    out: dict[str, str] = {}
    for r in records:
        # Support both `candidate` (fixture) and `candidate_name` (live state).
        name = r.get("candidate") or r.get("candidate_name") or ""
        if "," not in name:
            continue
        last, first = [s.strip() for s in name.split(",", 1)]
        first_word = first.split()[0] if first else ""
        if not (last and first_word):
            continue
        key = f"{last.lower()}|{first_word.lower()}"
        party = r.get("final_party") or r.get("detected_party")
        if not party:
            continue  # only emit entries we have a party tag for
        out[key] = party
    return out

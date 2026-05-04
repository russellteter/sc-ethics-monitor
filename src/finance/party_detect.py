"""Party detection with caching layer.

Wraps the existing :mod:`src.party_detector` (legacy, flat-import module) for
use by the finance scraper. The wrapped detector is expected to return a
``(party, confidence, source)`` triple for a candidate name + district. We
catch all exceptions and degrade to party ``"?"`` with the error message
stored in the cache so we can audit later.

The legacy :mod:`src.party_detector` module uses flat imports
(``from config import ...``), so we cannot import it as a package member
directly. :func:`make_real_detector` puts ``src/`` on ``sys.path`` and imports
``party_detector`` flat — and adapts its :class:`PartyResult` dataclass to
the ``(party, confidence, source)`` triple this layer expects.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Tuple

logger = logging.getLogger(__name__)

# Detector callable signature: (name, district) -> (party, confidence, source)
DetectorFn = Callable[[str, int], Tuple[str, str, str]]


def load_party_cache(path: Path) -> dict:
    """Load the on-disk party cache. Empty dict if missing or unreadable."""
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text() or "{}")
    except json.JSONDecodeError:
        logger.warning("party cache %s is corrupt; starting fresh", p)
        return {}


def save_party_cache(path: Path, data: dict) -> None:
    """Atomically write the cache via tmp+replace."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
    tmp.replace(p)


def detect_party_with_cache(
    *,
    cache_path: Path,
    cache_key: str,
    candidate_name: str,
    district: int,
    detector: DetectorFn,
) -> str:
    """Look up party for ``cache_key``; call ``detector`` on miss; persist.

    Returns the party letter (D/R/I/O/?). On exception, returns ``"?"`` and
    persists the error message to the cache for later inspection.
    """
    cache = load_party_cache(cache_path)
    if cache_key in cache and cache[cache_key].get("party"):
        return cache[cache_key]["party"]
    now = datetime.now(timezone.utc).isoformat()
    try:
        party, confidence, source = detector(candidate_name, district)
        cache[cache_key] = {
            "party": party,
            "confidence": confidence,
            "source": source,
            "detected_at": now,
        }
    except Exception as e:
        logger.warning(
            "party detection failed for %s D-%s: %s",
            candidate_name,
            district,
            e,
        )
        cache[cache_key] = {
            "party": "?",
            "confidence": "ERROR",
            "source": "exception",
            "error": str(e)[:200],
            "detected_at": now,
        }
    save_party_cache(cache_path, cache)
    return cache[cache_key]["party"]


def make_real_detector() -> DetectorFn:
    """Construct a :data:`DetectorFn` backed by the legacy :mod:`party_detector`.

    The legacy module uses flat imports (``from config import ...``), so we
    inject ``src/`` onto ``sys.path`` before importing it. We adapt the
    :class:`PartyResult` dataclass to a ``(party, confidence, source)`` triple.
    The legacy ``detect_party`` takes ``office`` (str), not ``district`` (int);
    we synthesize an SC House office string from the district number.

    If the legacy module cannot be imported (missing dependency, etc.), we
    return a stub detector that raises — :func:`detect_party_with_cache` will
    catch it and the candidate will be cached as ``"?"``.
    """
    import sys

    src_dir = str(Path(__file__).resolve().parent.parent)
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    try:
        import party_detector as legacy  # type: ignore[import-not-found]
    except Exception as e:
        logger.warning("legacy party_detector import failed: %s", e)
        err = e

        def _broken(_name: str, _district: int) -> Tuple[str, str, str]:
            raise RuntimeError(f"party_detector unavailable: {err}")

        return _broken

    def _detect(name: str, district: int) -> Tuple[str, str, str]:
        office = f"SC House of Representatives District {district}"
        result = legacy.detect_party(candidate_name=name, office=office)
        # Legacy returns a PartyResult dataclass; attribute access only.
        party = getattr(result, "party", None) or "?"
        confidence = getattr(result, "confidence", None) or "MEDIUM"
        source = getattr(result, "source", None) or "legacy"
        return party, confidence, source

    return _detect

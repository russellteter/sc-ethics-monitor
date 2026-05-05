"""Lightweight 'are there new filings?' probe.

Used by the Sunday cron to short-circuit a full Playwright run when no new
reportIds have appeared on the Ethics recent-reports index. Reads/writes
``data/recent_reports_state.json``.

Wiring is intentionally deferred: the full integration into ``__main__`` is
out of scope for the current plan (the recent-reports HTML grep needs more
work to be reliable). Tests exercise the contract; production wiring is a
follow-up. See plan Phase 3.2 Step 5 for context.
"""
from __future__ import annotations

import json
from pathlib import Path

STATE_FILE = (
    Path(__file__).resolve().parents[2] / "data" / "recent_reports_state.json"
)


def _diff_report_ids(current: set[str], previous: set[str]) -> set[str]:
    """Return ids present in ``current`` but missing from ``previous``."""
    return current - previous


def has_new_reports(state_path: Path, current_ids: set[str]) -> bool:
    """Return True if ``current_ids`` contains any id not in the saved state.

    Treats a missing or corrupt state file as "no prior knowledge" and
    returns True so the caller falls through to a full scrape.
    """
    if not state_path.exists():
        return True
    try:
        payload = json.loads(state_path.read_text())
    except (json.JSONDecodeError, OSError):
        return True
    previous = set(payload.get("recent_report_ids", []))
    return bool(_diff_report_ids(current_ids, previous))


def save_recent_ids(state_path: Path, ids: set[str]) -> None:
    """Persist the canonical sorted list of recent reportIds to ``state_path``."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps({"recent_report_ids": sorted(ids)}, indent=2)
    )

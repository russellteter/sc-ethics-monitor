"""Smoke tests for the pure helper in :mod:`src.finance.playwright_ops`.

The Playwright-driven functions themselves are exercised by integration tests.
"""
from src.finance.playwright_ops import _normalize_row


def test_normalize_quarterly_row():
    raw = {
        "reportId": "418208",
        "url": "https://example.com/r/418208",
        "cells": ["Quarterly Report", "Q1 2026", "04/10/2026", "View"],
    }
    out = _normalize_row(raw)
    assert out["report_type"] == "Quarterly"
    assert out["period_label"] == "Q1 2026"
    assert "/" in out["filed_date"]
    assert out["is_amended"] is False
    assert out["reportId"] == "418208"


def test_normalize_amended():
    raw = {
        "reportId": "1",
        "url": "u",
        "cells": ["Quarterly Report (Amended)", "Q1 2026", "04/15/2026"],
    }
    out = _normalize_row(raw)
    assert out["is_amended"] is True
    assert out["report_type"] == "Quarterly"


def test_normalize_initial():
    raw = {
        "reportId": "9",
        "url": "u9",
        "cells": ["Initial Report", "", "01/15/2026"],
    }
    out = _normalize_row(raw)
    assert out["report_type"] == "Initial"
    assert out["filed_date"] == "01/15/2026"


def test_normalize_pre_election():
    raw = {"reportId": "x", "url": "u", "cells": ["Pre-Election Report", "", "10/20/2026"]}
    assert _normalize_row(raw)["report_type"] == "Pre-Election"


def test_normalize_pre_election_with_space():
    raw = {"reportId": "x", "url": "u", "cells": ["Pre Election Report", "", "10/20/2026"]}
    assert _normalize_row(raw)["report_type"] == "Pre-Election"


def test_normalize_final():
    raw = {"reportId": "x", "url": "u", "cells": ["Final Report", "", "12/31/2026"]}
    assert _normalize_row(raw)["report_type"] == "Final"


def test_normalize_unknown_type_falls_through_to_other():
    raw = {"reportId": "x", "url": "u", "cells": ["Mystery Report", "", "01/01/2026"]}
    assert _normalize_row(raw)["report_type"] == "Other"


def test_normalize_handles_empty_cells():
    raw = {"reportId": None, "url": None, "cells": []}
    out = _normalize_row(raw)
    assert out["report_type"] == "Other"
    assert out["filed_date"] == ""
    assert out["period_label"] == ""
    assert out["is_amended"] is False

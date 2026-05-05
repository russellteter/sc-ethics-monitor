"""Tests for the internal recent-reports probe.

The probe lets the Sunday cron short-circuit a full Playwright run when
no new reportIds have appeared on the Ethics recent-reports index.
"""
from __future__ import annotations

import json

from src.finance.probe import _diff_report_ids, has_new_reports, save_recent_ids


def test_diff_empty_when_identical():
    assert _diff_report_ids({"1", "2", "3"}, {"1", "2", "3"}) == set()


def test_diff_returns_new_ids():
    assert _diff_report_ids({"1", "2", "3"}, {"1", "2"}) == {"3"}


def test_diff_ignores_removed_ids():
    # current is a strict subset of previous → nothing new
    assert _diff_report_ids({"1", "2"}, {"1", "2", "3"}) == set()


def test_has_new_reports_returns_true_on_first_run(tmp_path):
    state = tmp_path / "state.json"
    assert has_new_reports(state, current_ids={"1", "2"}) is True


def test_has_new_reports_returns_false_when_subset(tmp_path):
    state = tmp_path / "state.json"
    state.write_text('{"recent_report_ids":["1","2","3"]}')
    assert has_new_reports(state, current_ids={"1", "2"}) is False


def test_has_new_reports_returns_true_when_new_id_present(tmp_path):
    state = tmp_path / "state.json"
    state.write_text('{"recent_report_ids":["1","2"]}')
    assert has_new_reports(state, current_ids={"1", "2", "3"}) is True


def test_has_new_reports_handles_corrupt_state(tmp_path):
    state = tmp_path / "state.json"
    state.write_text("not json {")
    # Corrupt state should be treated as "no prior knowledge" → assume new.
    assert has_new_reports(state, current_ids={"1"}) is True


def test_save_recent_ids_creates_parent_and_sorts(tmp_path):
    state = tmp_path / "nested" / "state.json"
    save_recent_ids(state, {"3", "1", "2"})
    payload = json.loads(state.read_text())
    assert payload == {"recent_report_ids": ["1", "2", "3"]}


def test_save_then_has_new_roundtrip(tmp_path):
    state = tmp_path / "state.json"
    save_recent_ids(state, {"1", "2"})
    assert has_new_reports(state, current_ids={"1", "2"}) is False
    assert has_new_reports(state, current_ids={"1", "2", "9"}) is True

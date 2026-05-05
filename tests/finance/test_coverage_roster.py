"""Tests for coverage_roster fetcher + filter."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import httpx
import pytest

from src.finance.coverage_roster import (
    DEFAULT_COVERAGE_URL,
    fetch_coverage_candidates,
    load_dem_house_roster_from_coverage,
)


SAMPLE = {
    "lastUpdated": "2026-05-03T23:12:07Z",
    "house": {
        "1": {
            "districtNumber": 1,
            "candidates": [
                {"name": "Brittany June Lynch", "party": "Democratic", "status": "filed"},
                {"name": "Bobby R Smith", "party": "Republican", "status": "filed"},
            ],
        },
        "75": {
            "districtNumber": 75,
            "candidates": [
                {"name": "Heather Bauer", "party": "Democratic", "status": "filed",
                 "isIncumbent": True},
            ],
        },
        "70": {
            "districtNumber": 70,
            "candidates": [
                {"name": "Wendy Brawley", "party": "Democratic", "status": "filed"},
                {"name": "Alice Doe", "party": "Democratic", "status": "filed"},
                {"name": "John Q Public", "party": "Libertarian", "status": "filed"},
            ],
        },
        "99": {
            "districtNumber": 99,
            "candidates": [
                {"name": "Withdrawn Cand", "party": "Democratic", "status": "withdrawn"},
            ],
        },
    },
    "senate": {},
}


def test_filters_to_democratic_house_only():
    roster = load_dem_house_roster_from_coverage(SAMPLE)
    parties = {c.party for c in roster}
    assert parties == {"D"}
    names = sorted(c.name for c in roster)
    assert names == ["Alice Doe", "Brittany June Lynch", "Heather Bauer", "Wendy Brawley"]


def test_excludes_withdrawn():
    roster = load_dem_house_roster_from_coverage(SAMPLE)
    assert all(c.name != "Withdrawn Cand" for c in roster)


def test_handles_multiple_dems_per_district():
    roster = load_dem_house_roster_from_coverage(SAMPLE)
    d70 = [c for c in roster if c.district == 70]
    assert len(d70) == 2
    assert {c.name for c in d70} == {"Wendy Brawley", "Alice Doe"}


def test_id_slug_format():
    roster = load_dem_house_roster_from_coverage(SAMPLE)
    bauer = next(c for c in roster if c.name == "Heather Bauer")
    assert bauer.id == "bauer-heather-75"
    assert bauer.district == 75
    assert bauer.office == "SC House of Representatives District 75"


def test_office_string_compatible_with_existing_house_regex():
    from src.finance.roster import _is_state_house
    roster = load_dem_house_roster_from_coverage(SAMPLE)
    assert all(_is_state_house(c.office) for c in roster)


def test_dedup_same_id():
    data = {
        "house": {"75": {"candidates": [
            {"name": "Heather Bauer", "party": "Democratic"},
            {"name": "Heather Bauer", "party": "Democratic"},  # duplicate
        ]}},
        "senate": {},
    }
    roster = load_dem_house_roster_from_coverage(data)
    assert len(roster) == 1


def test_handles_empty_house():
    roster = load_dem_house_roster_from_coverage({"house": {}, "senate": {}})
    assert roster == []


def test_fetch_writes_cache(tmp_path, mocker):
    cache = tmp_path / "cov.json"
    resp = MagicMock(status_code=200)
    resp.raise_for_status = MagicMock()
    resp.json.return_value = SAMPLE
    mocker.patch("httpx.get", return_value=resp)
    out = fetch_coverage_candidates(url="http://example/x.json", cache_path=cache)
    assert out == SAMPLE
    assert json.loads(cache.read_text()) == SAMPLE


def test_fetch_falls_back_to_cache_on_http_error(tmp_path, mocker):
    cache = tmp_path / "cov.json"
    cache.write_text(json.dumps(SAMPLE))
    mocker.patch("httpx.get", side_effect=httpx.HTTPError("boom"))
    out = fetch_coverage_candidates(url="http://example/x.json", cache_path=cache)
    assert out == SAMPLE


def test_fetch_raises_when_no_cache_and_http_fails(tmp_path, mocker):
    cache = tmp_path / "missing.json"
    mocker.patch("httpx.get", side_effect=httpx.HTTPError("boom"))
    with pytest.raises(httpx.HTTPError):
        fetch_coverage_candidates(url="http://example/x.json", cache_path=cache)

import json

import pytest

from src.finance.resolver import (
    UrlParams,
    resolve_from_cache,
    resolve_from_ethics_state,
    resolve_with_fallback,
    update_cache,
)


def test_cache_hit_returns_url_params(tmp_path):
    cache_file = tmp_path / "cache.json"
    cache_file.write_text(
        json.dumps(
            {"bauer-heather-75": {"personId": "45921", "seiId": "51547", "officeId": "71866"}}
        )
    )
    params = resolve_from_cache(cache_file, "bauer-heather-75")
    assert params == UrlParams(personId="45921", seiId="51547", officeId="71866")


def test_cache_miss_returns_none(tmp_path):
    cache_file = tmp_path / "cache.json"
    cache_file.write_text("{}")
    assert resolve_from_cache(cache_file, "kirby-roger-61") is None


def test_cache_missing_file_returns_none(tmp_path):
    """A non-existent cache file is a soft miss, not an error."""
    assert resolve_from_cache(tmp_path / "does-not-exist.json", "anything") is None


def test_ethics_state_lookup_by_name(ethics_state_path):
    params = resolve_from_ethics_state(ethics_state_path, "Heather Bauer", district=75)
    assert params == UrlParams(personId="45921", seiId="51547", officeId="71866")


def test_ethics_state_returns_none_for_unknown(ethics_state_path):
    assert resolve_from_ethics_state(ethics_state_path, "Roger Kirby", district=61) is None


def test_ethics_state_returns_none_when_district_mismatches(ethics_state_path):
    """Right name, wrong district → no match."""
    assert resolve_from_ethics_state(ethics_state_path, "Heather Bauer", district=99) is None


def test_ethics_state_missing_file_returns_none(tmp_path):
    assert resolve_from_ethics_state(tmp_path / "missing.json", "Anyone", district=1) is None


def test_fallback_uses_cache_first(tmp_path, ethics_state_path, mocker):
    cache_file = tmp_path / "cache.json"
    cache_file.write_text(
        json.dumps(
            {"bauer-heather-75": {"personId": "99999", "seiId": "0", "officeId": "0"}}
        )
    )
    playwright_mock = mocker.MagicMock()
    params = resolve_with_fallback(
        candidate_id="bauer-heather-75",
        candidate_name="Heather Bauer",
        district=75,
        cache_path=cache_file,
        ethics_state_path=ethics_state_path,
        playwright_search=playwright_mock,
    )
    assert params.personId == "99999"
    playwright_mock.assert_not_called()


def test_fallback_uses_ethics_state_when_cache_miss(tmp_path, ethics_state_path, mocker):
    cache_file = tmp_path / "cache.json"
    cache_file.write_text("{}")
    playwright_mock = mocker.MagicMock()
    params = resolve_with_fallback(
        candidate_id="bauer-heather-75",
        candidate_name="Heather Bauer",
        district=75,
        cache_path=cache_file,
        ethics_state_path=ethics_state_path,
        playwright_search=playwright_mock,
    )
    assert params == UrlParams("45921", "51547", "71866")
    playwright_mock.assert_not_called()


def test_fallback_falls_through_to_playwright(tmp_path, ethics_state_path, mocker):
    cache_file = tmp_path / "cache.json"
    cache_file.write_text("{}")
    playwright_mock = mocker.MagicMock(return_value=UrlParams("123", "456", "789"))
    params = resolve_with_fallback(
        candidate_id="kirby-roger-61",
        candidate_name="Roger Kirby",
        district=61,
        cache_path=cache_file,
        ethics_state_path=ethics_state_path,
        playwright_search=playwright_mock,
    )
    assert params == UrlParams("123", "456", "789")
    playwright_mock.assert_called_once_with("Roger Kirby", 61)


def test_fallback_returns_none_when_all_three_miss(tmp_path, ethics_state_path, mocker):
    cache_file = tmp_path / "cache.json"
    cache_file.write_text("{}")
    playwright_mock = mocker.MagicMock(return_value=None)
    params = resolve_with_fallback(
        candidate_id="ghost-x-1",
        candidate_name="Ghost X",
        district=1,
        cache_path=cache_file,
        ethics_state_path=ethics_state_path,
        playwright_search=playwright_mock,
    )
    assert params is None


def test_update_cache_writes_entry(tmp_path):
    cache_file = tmp_path / "cache.json"
    cache_file.write_text("{}")
    update_cache(cache_file, "kirby-roger-61", UrlParams("1", "2", "3"))
    data = json.loads(cache_file.read_text())
    assert data["kirby-roger-61"] == {"personId": "1", "seiId": "2", "officeId": "3"}


def test_update_cache_creates_new_file(tmp_path):
    cache_file = tmp_path / "new.json"
    update_cache(cache_file, "x", UrlParams("1", "2", "3"))
    assert cache_file.exists()
    data = json.loads(cache_file.read_text())
    assert "x" in data

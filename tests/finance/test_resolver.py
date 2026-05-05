import json

import pytest

from src.finance.resolver import (
    UrlParams,
    find_latest_quarterly_from_rows,
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


def test_ethics_state_live_shape_dict_keyed_by_report_id_with_ids_in_url(tmp_path):
    """Mirrors the real state.json: dict of {reportId -> entry}, ``candidate_name`` field,
    and personId/seiId/officeId only in the ``url`` query string."""
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({
        "reports_with_metadata": {
            "417093": {
                "candidate_name": "Morgan, Tyler A",
                "office": "SC House of Representatives District 91",
                "report_name": "Initial Report 2025",
                "filed_date": "2026-01-06",
                "url": "https://ethicsfiling.sc.gov/public/x?personId=55826&seiId=57496&officeId=78561&reportId=417093",
            }
        }
    }))
    params = resolve_from_ethics_state(state_path, "Tyler Morgan", district=91)
    assert params == UrlParams(personId="55826", seiId="57496", officeId="78561")


def test_ethics_state_district_match_is_exact_not_substring(tmp_path):
    """``District 3`` must not match office text containing ``District 30``."""
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({
        "reports_with_metadata": [
            {
                "candidate_name": "Doe, Jane",
                "office": "SC House of Representatives District 30",
                "url": "https://ethicsfiling.sc.gov/x?personId=1&seiId=2&officeId=3&reportId=9",
            }
        ]
    }))
    assert resolve_from_ethics_state(state_path, "Jane Doe", district=3) is None
    assert resolve_from_ethics_state(state_path, "Jane Doe", district=30) == UrlParams("1", "2", "3")


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


# ----- find_latest_quarterly_from_rows -----


def test_picks_newest_quarterly():
    rows = [
        {"report_type": "Initial", "filed_date": "2026-01-15", "reportId": "1", "url": "u1"},
        {"report_type": "Quarterly", "filed_date": "2026-01-15", "reportId": "2", "url": "u2",
         "period_label": "Q4 2025", "is_amended": False},
        {"report_type": "Quarterly", "filed_date": "2026-04-10", "reportId": "3", "url": "u3",
         "period_label": "Q1 2026", "is_amended": False},
    ]
    result = find_latest_quarterly_from_rows(rows)
    assert result["reportId"] == "3"


def test_returns_none_when_no_quarterly():
    rows = [
        {"report_type": "Initial", "filed_date": "2026-01-15", "reportId": "1", "url": "u1"}
    ]
    assert find_latest_quarterly_from_rows(rows) is None


def test_returns_none_when_rows_empty():
    assert find_latest_quarterly_from_rows([]) is None


def test_amendment_supersedes_when_newer():
    rows = [
        {"report_type": "Quarterly", "filed_date": "2026-04-10", "reportId": "3", "url": "u3",
         "period_label": "Q1 2026", "is_amended": False},
        {"report_type": "Quarterly", "filed_date": "2026-04-15", "reportId": "4", "url": "u4",
         "period_label": "Q1 2026", "is_amended": True},
    ]
    result = find_latest_quarterly_from_rows(rows)
    assert result["reportId"] == "4"
    assert result["is_amended"] is True


def test_period_label_beats_filed_date_for_recency():
    """Live Ethics pages show an "updated" filed_date that doesn't agree with the
    actual reporting period — period_label is authoritative for which quarter is
    most recent."""
    rows = [
        # Older period, "updated" recently — must NOT win
        {"report_type": "Quarterly", "filed_date": "11/8/2022", "reportId": "327668",
         "url": "u-old", "period_label": "Quarter 2, 2022 Report", "is_amended": False},
        # Newer period, older "updated" date — must win
        {"report_type": "Quarterly", "filed_date": "11/5/2024", "reportId": "407145",
         "url": "u-new", "period_label": "Quarter 4, 2023 Report", "is_amended": False},
    ]
    result = find_latest_quarterly_from_rows(rows)
    assert result["reportId"] == "407145"


def test_mm_dd_yyyy_dates_compared_chronologically_not_lexicographically():
    """``"11/8/2022"`` vs ``"11/5/2024"`` — lex sort would pick 2022 (wrong)."""
    rows = [
        {"report_type": "Quarterly", "filed_date": "11/8/2022", "reportId": "A",
         "url": "uA", "period_label": "Quarter 1, 2026 Report", "is_amended": False},
        {"report_type": "Quarterly", "filed_date": "11/5/2024", "reportId": "B",
         "url": "uB", "period_label": "Quarter 1, 2026 Report", "is_amended": False},
    ]
    # Same period label → tiebreak on filed_date. Must pick 2024 over 2022.
    result = find_latest_quarterly_from_rows(rows)
    assert result["reportId"] == "B"

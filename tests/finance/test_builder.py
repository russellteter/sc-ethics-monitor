import json

import pytest

from src.finance.builder import ScrapeFailureRateExceeded, build_artifact
from src.finance.parser import ReportNumbers
from src.finance.resolver import UrlParams
from src.finance.roster import Candidate


def _stub_candidates():
    return [
        Candidate(
            id="bauer-heather-75",
            name="Heather Bauer",
            district=75,
            party="D",
            office="SC House of Representatives District 75",
        ),
        Candidate(
            id="kirby-roger-61",
            name="Roger Kirby",
            district=61,
            party="D",
            office="SC House of Representatives District 61",
        ),
    ]


def test_build_artifact_handles_filed_and_not_filed(tmp_path):
    out_path = tmp_path / "house_finance.json"
    cache_path = tmp_path / "cache.json"
    cache_path.write_text("{}")

    def resolve(cid, name, district):
        if cid == "bauer-heather-75":
            return UrlParams("45921", "51547", "71866")
        return None

    def find_latest(params):
        return {
            "reportId": "418208",
            "report_type": "Quarterly",
            "period_label": "Q1 2026",
            "filed_date": "2026-04-10",
            "url": "https://example.com/r/418208",
            "is_amended": False,
        }

    def fetch_and_parse(url):
        return ReportNumbers(32806.90, 89372.11, 68448.57)

    build_artifact(
        candidates=_stub_candidates(),
        out_path=out_path,
        cache_path=cache_path,
        resolve_fn=resolve,
        find_latest_fn=find_latest,
        fetch_and_parse_fn=fetch_and_parse,
        cycle="2026",
        now_iso="2026-05-04T23:00:00-04:00",
    )

    out = json.loads(out_path.read_text())
    assert out["schema_version"] == 1
    assert out["generated_at"] == "2026-05-04T23:00:00-04:00"
    assert out["cycle"] == "2026"
    assert out["stats"]["total_dem_house"] == 2
    assert out["stats"]["filed"] == 1
    assert out["stats"]["not_filed"] == 1
    assert out["stats"]["scrape_failed"] == 0
    bauer = next(c for c in out["candidates"] if c["id"] == "bauer-heather-75")
    assert bauer["filing_status"] == "filed"
    assert bauer["latest_report"]["cash_on_hand"] == 68448.57
    assert bauer["latest_report"]["period_raised"] == 32806.90
    assert bauer["personId"] == "45921"
    kirby = next(c for c in out["candidates"] if c["id"] == "kirby-roger-61")
    assert kirby["filing_status"] == "not_filed"
    assert kirby["latest_report"] is None


def test_build_artifact_handles_no_quarterly_yet(tmp_path):
    """``find_latest_fn`` returning None → ``filing_status='not_filed'`` not failure."""
    out_path = tmp_path / "out.json"
    cache_path = tmp_path / "cache.json"
    cache_path.write_text("{}")

    def resolve(*a, **k):
        return UrlParams("1", "2", "3")

    def find_latest(*a, **k):
        return None

    def fetch_and_parse(*a, **k):
        raise AssertionError("should not be called")

    build_artifact(
        candidates=[
            Candidate(
                id="x-1",
                name="X One",
                district=1,
                party="D",
                office="SC House of Representatives District 1",
            )
        ],
        out_path=out_path,
        cache_path=cache_path,
        resolve_fn=resolve,
        find_latest_fn=find_latest,
        fetch_and_parse_fn=fetch_and_parse,
        cycle="2026",
        now_iso="2026-05-04T23:00:00-04:00",
    )
    out = json.loads(out_path.read_text())
    assert out["candidates"][0]["filing_status"] == "not_filed"
    assert out["stats"]["not_filed"] == 1


def test_build_artifact_carries_forward_on_scrape_failure(tmp_path):
    out_path = tmp_path / "house_finance.json"
    out_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": "2026-04-27T23:00:00-04:00",
                "cycle": "2026",
                "candidates": [
                    {
                        "id": "bauer-heather-75",
                        "name": "Heather Bauer",
                        "district": 75,
                        "party": "D",
                        "personId": "45921",
                        "seiId": "51547",
                        "officeId": "71866",
                        "filing_status": "filed",
                        "latest_report": {
                            "reportId": "418208",
                            "report_type": "Quarterly",
                            "period_label": "Q1 2026",
                            "filed_date": "2026-04-10",
                            "url": "https://example.com/r/418208",
                            "period_raised": 100.0,
                            "total_raised": 200.0,
                            "cash_on_hand": 50.0,
                            "is_amended": False,
                        },
                        "history": [],
                        "last_error": None,
                    }
                ],
                "stats": {},
            }
        )
    )
    cache_path = tmp_path / "cache.json"
    cache_path.write_text("{}")

    def resolve(*a, **k):
        return UrlParams("45921", "51547", "71866")

    def find_latest(*a, **k):
        return {
            "reportId": "418208",
            "url": "u",
            "report_type": "Quarterly",
            "period_label": "Q1 2026",
            "filed_date": "2026-04-10",
            "is_amended": False,
        }

    def fetch_and_parse(*a, **k):
        raise RuntimeError("boom")

    build_artifact(
        candidates=[
            Candidate(
                id="bauer-heather-75",
                name="Heather Bauer",
                district=75,
                party="D",
                office="SC House of Representatives District 75",
            )
        ],
        out_path=out_path,
        cache_path=cache_path,
        resolve_fn=resolve,
        find_latest_fn=find_latest,
        fetch_and_parse_fn=fetch_and_parse,
        cycle="2026",
        now_iso="2026-05-04T23:00:00-04:00",
        max_failure_rate=1.0,  # this test isn't about the threshold
    )

    out = json.loads(out_path.read_text())
    bauer = out["candidates"][0]
    assert bauer["filing_status"] == "scrape_failed"
    assert bauer["latest_report"]["cash_on_hand"] == 50.0  # carried forward
    assert "boom" in bauer["last_error"]


def test_build_artifact_no_carry_forward_when_no_prior(tmp_path):
    """Scrape fails and no prior record exists → status=scrape_failed, latest_report=None."""
    out_path = tmp_path / "out.json"  # does not exist yet
    cache_path = tmp_path / "cache.json"
    cache_path.write_text("{}")

    def resolve(*a, **k):
        return UrlParams("1", "2", "3")

    def find_latest(*a, **k):
        return {"reportId": "1", "url": "u", "report_type": "Quarterly",
                "period_label": "Q1 2026", "filed_date": "2026-04-10", "is_amended": False}

    def fetch_and_parse(*a, **k):
        raise RuntimeError("nope")

    build_artifact(
        candidates=[
            Candidate(
                id="x-1",
                name="X",
                district=1,
                party="D",
                office="SC House of Representatives District 1",
            )
        ],
        out_path=out_path,
        cache_path=cache_path,
        resolve_fn=resolve,
        find_latest_fn=find_latest,
        fetch_and_parse_fn=fetch_and_parse,
        cycle="2026",
        now_iso="2026-05-04T23:00:00-04:00",
        max_failure_rate=1.0,
    )
    out = json.loads(out_path.read_text())
    assert out["candidates"][0]["filing_status"] == "scrape_failed"
    assert out["candidates"][0]["latest_report"] is None
    assert out["stats"]["scrape_failed"] == 1


def test_stats_compute_median_and_top(tmp_path):
    out_path = tmp_path / "out.json"
    cache_path = tmp_path / "cache.json"
    cache_path.write_text("{}")

    def resolve(cid, *a, **k):
        return UrlParams("1", "2", "3")

    def find_latest(*a, **k):
        return {
            "reportId": "1",
            "url": "u",
            "report_type": "Quarterly",
            "period_label": "Q1 2026",
            "filed_date": "2026-04-10",
            "is_amended": False,
        }

    by_id = {
        "a-1": ReportNumbers(10.0, 100.0, 100.0),
        "b-2": ReportNumbers(20.0, 200.0, 500.0),
        "c-3": ReportNumbers(30.0, 300.0, 1000.0),
    }
    def fetch_and_parse(url):
        # url is unused by stub, route by call order via consumed iterator
        return next(_iter)

    _iter = iter([by_id["a-1"], by_id["b-2"], by_id["c-3"]])
    cands = [
        Candidate(id="a-1", name="A One", district=1, party="D",
                  office="SC House of Representatives District 1"),
        Candidate(id="b-2", name="B Two", district=2, party="D",
                  office="SC House of Representatives District 2"),
        Candidate(id="c-3", name="C Three", district=3, party="D",
                  office="SC House of Representatives District 3"),
    ]
    build_artifact(
        candidates=cands,
        out_path=out_path,
        cache_path=cache_path,
        resolve_fn=resolve,
        find_latest_fn=find_latest,
        fetch_and_parse_fn=fetch_and_parse,
        cycle="2026",
        now_iso="2026-05-04T23:00:00-04:00",
    )
    out = json.loads(out_path.read_text())
    stats = out["stats"]
    assert stats["filed"] == 3
    assert stats["median_coh"] == 500.0
    assert stats["top_coh"] == 1000.0
    assert stats["top_coh_candidate"] == "C Three"
    assert stats["top_coh_district"] == 3
    assert stats["total_q_raised"] == 60.0
    assert stats["total_coh_all"] == 1600.0


def test_raises_when_failure_rate_exceeds_threshold(tmp_path):
    """When >max_failure_rate of candidates fail, builder raises after writing the artifact."""
    out_path = tmp_path / "house_finance.json"
    cache_path = tmp_path / "cache.json"
    cache_path.write_text("{}")
    cands = [
        Candidate(
            id=f"x-{i}",
            name=f"X {i}",
            district=i + 1,
            party="D",
            office="SC House of Representatives District 1",
        )
        for i in range(10)
    ]

    def resolve(*a, **k):
        return UrlParams("1", "2", "3")

    def find_latest(*a, **k):
        return {
            "reportId": "1",
            "url": "u",
            "report_type": "Quarterly",
            "period_label": "Q1",
            "filed_date": "2026-04-10",
            "is_amended": False,
        }

    def fetch_and_parse(*a, **k):
        raise RuntimeError("boom")

    with pytest.raises(ScrapeFailureRateExceeded):
        build_artifact(
            candidates=cands,
            out_path=out_path,
            cache_path=cache_path,
            resolve_fn=resolve,
            find_latest_fn=find_latest,
            fetch_and_parse_fn=fetch_and_parse,
            cycle="2026",
            now_iso="2026-05-04T23:00:00-04:00",
            max_failure_rate=0.2,
        )
    # Artifact still gets written so partial progress is preserved.
    assert out_path.exists()
    out = json.loads(out_path.read_text())
    assert out["stats"]["scrape_failed"] == 10


def test_below_threshold_does_not_raise(tmp_path):
    """If failure rate is at or below threshold, build_artifact returns normally."""
    out_path = tmp_path / "out.json"
    cache_path = tmp_path / "cache.json"
    cache_path.write_text("{}")
    cands = [
        Candidate(
            id=f"x-{i}",
            name=f"X {i}",
            district=i + 1,
            party="D",
            office="SC House of Representatives District 1",
        )
        for i in range(10)
    ]

    def resolve(cid, *a, **k):
        return UrlParams("1", "2", "3")

    def find_latest(*a, **k):
        return {
            "reportId": "1",
            "url": "u",
            "report_type": "Quarterly",
            "period_label": "Q1",
            "filed_date": "2026-04-10",
            "is_amended": False,
        }

    call_n = {"i": 0}

    def fetch_and_parse(*a, **k):
        call_n["i"] += 1
        if call_n["i"] <= 1:
            raise RuntimeError("only first one fails")
        return ReportNumbers(10.0, 100.0, 50.0)

    build_artifact(
        candidates=cands,
        out_path=out_path,
        cache_path=cache_path,
        resolve_fn=resolve,
        find_latest_fn=find_latest,
        fetch_and_parse_fn=fetch_and_parse,
        cycle="2026",
        now_iso="2026-05-04T23:00:00-04:00",
        max_failure_rate=0.2,
    )
    out = json.loads(out_path.read_text())
    assert out["stats"]["scrape_failed"] == 1
    assert out["stats"]["filed"] == 9


def test_updates_cache_when_resolve_succeeds(tmp_path):
    out_path = tmp_path / "out.json"
    cache_path = tmp_path / "cache.json"
    cache_path.write_text("{}")

    def resolve(*a, **k):
        return UrlParams("9", "8", "7")

    def find_latest(*a, **k):
        return None

    def fetch_and_parse(*a, **k):
        raise AssertionError("not called")

    build_artifact(
        candidates=[
            Candidate(id="kirby-roger-61", name="Roger Kirby", district=61,
                      party="D", office="SC House of Representatives District 61")
        ],
        out_path=out_path,
        cache_path=cache_path,
        resolve_fn=resolve,
        find_latest_fn=find_latest,
        fetch_and_parse_fn=fetch_and_parse,
        cycle="2026",
        now_iso="2026-05-04T23:00:00-04:00",
    )
    cache = json.loads(cache_path.read_text())
    assert cache["kirby-roger-61"] == {"personId": "9", "seiId": "8", "officeId": "7"}

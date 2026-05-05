"""Tests for :mod:`src.finance.__main__` CLI entry point.

These mock the heavy dependencies (Playwright, network) and exercise the
control-flow branches: arg parsing, dry-run, coverage fetch failure, success
path, failure-rate exit code.
"""
import json

import pytest


def test_help_does_not_blow_up(capsys):
    """`--help` should print usage and exit cleanly."""
    from src.finance.__main__ import main

    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "Scrape SC House Dem campaign-finance data" in out


def test_dry_run_returns_zero_when_coverage_unreachable(monkeypatch, capsys):
    """When coverage source is unreachable AND no cache, --dry-run still exits 0."""
    from src.finance.__main__ import main

    def boom(*a, **kw):
        raise RuntimeError("simulated outage")

    monkeypatch.setattr("src.finance.__main__.fetch_coverage_candidates", boom)
    rc = main(["--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "coverage source unreachable" in out


def test_non_dry_run_returns_2_when_coverage_unreachable(monkeypatch):
    """A real run without coverage source returns 2 (no work to do)."""
    from src.finance.__main__ import main

    def boom(*a, **kw):
        raise RuntimeError("simulated outage")

    monkeypatch.setattr("src.finance.__main__.fetch_coverage_candidates", boom)
    assert main([]) == 2


def test_dry_run_loads_roster_and_returns_zero(monkeypatch, capsys):
    """--dry-run loads the roster from coverage source and exits 0."""
    from src.finance.__main__ import main

    sample = {
        "lastUpdated": "2026-05-04T12:00:00Z",
        "house": {"75": {"candidates": [
            {"name": "Heather Bauer", "party": "Democratic", "status": "filed"},
        ]}},
        "senate": {},
    }
    monkeypatch.setattr(
        "src.finance.__main__.fetch_coverage_candidates",
        lambda **kw: sample,
    )
    rc = main(["--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "roster size: 1 Dem House candidates" in out


def test_full_run_writes_artifact(monkeypatch, tmp_path):
    """Happy-path full run: produces a populated house_finance.json."""
    from src.finance import config
    from src.finance.__main__ import main
    from src.finance.parser import ReportNumbers
    from src.finance.resolver import UrlParams

    out_path = tmp_path / "house_finance.json"
    cache_path = tmp_path / "cache.json"
    # Pre-populate the cache so resolve_with_fallback hits cache first
    # (matches production behaviour: most candidates resolve from disk cache).
    cache_path.write_text(json.dumps({
        "bauer-heather-75": {"personId": "1", "seiId": "2", "officeId": "3"},
    }))
    ethics = tmp_path / "ethics.json"
    ethics.write_text("{}")

    monkeypatch.setattr(config, "HOUSE_FINANCE_PATH", out_path)
    monkeypatch.setattr(config, "PERSONID_CACHE_PATH", cache_path)
    monkeypatch.setattr(config, "ETHICS_STATE_PATH", ethics)

    sample = {
        "lastUpdated": "2026-05-04T12:00:00Z",
        "house": {"75": {"candidates": [
            {"name": "Heather Bauer", "party": "Democratic", "status": "filed"},
        ]}},
        "senate": {},
    }
    monkeypatch.setattr(
        "src.finance.__main__.fetch_coverage_candidates",
        lambda **kw: sample,
    )
    monkeypatch.setattr(
        "src.finance.__main__.fetch_reports_list",
        lambda params: [{
            "reportId": "418208",
            "url": "https://example.com/r/418208",
            "report_type": "Quarterly",
            "filed_date": "2026-04-10",
            "period_label": "Q1 2026",
            "is_amended": False,
        }],
    )
    monkeypatch.setattr(
        "src.finance.__main__.fetch_html",
        lambda url, **kw: "<html>Cash Contributions Total Campaign Funds</html>",
    )
    monkeypatch.setattr(
        "src.finance.__main__.parse_report_detail",
        lambda html: ReportNumbers(32806.90, 89372.11, 68448.57),
    )
    monkeypatch.setattr(
        "src.finance.__main__.make_playwright_fetcher",
        lambda: (lambda url: "<html>fake</html>"),
    )

    rc = main([])
    assert rc == 0
    artifact = json.loads(out_path.read_text())
    assert artifact["stats"]["filed"] == 1
    assert artifact["candidates"][0]["latest_report"]["cash_on_hand"] == 68448.57


def test_full_run_returns_2_on_failure_rate_breach(monkeypatch, tmp_path):
    """Failure-rate exceeded → exit code 2 (artifact still written).

    Pre-populate cache so all 5 candidates resolve, then make fetch_html
    boom so every scrape fails → triggers the failure-rate threshold.
    """
    from src.finance import config
    from src.finance.__main__ import main
    from src.finance.resolver import UrlParams

    out_path = tmp_path / "house_finance.json"
    cache_path = tmp_path / "cache.json"
    # Pre-populate cache so all 5 candidates resolve (no Playwright needed).
    cache_path.write_text(json.dumps({
        f"cand-x{i}-{i + 1}": {"personId": "1", "seiId": "2", "officeId": "3"}
        for i in range(5)
    }))
    ethics = tmp_path / "ethics.json"
    ethics.write_text("{}")

    monkeypatch.setattr(config, "HOUSE_FINANCE_PATH", out_path)
    monkeypatch.setattr(config, "PERSONID_CACHE_PATH", cache_path)
    monkeypatch.setattr(config, "ETHICS_STATE_PATH", ethics)

    sample = {
        "lastUpdated": "2026-05-04T12:00:00Z",
        "house": {str(i + 1): {"candidates": [
            {"name": f"X{i} Cand", "party": "Democratic", "status": "filed"},
        ]} for i in range(5)},
        "senate": {},
    }
    monkeypatch.setattr(
        "src.finance.__main__.fetch_coverage_candidates",
        lambda **kw: sample,
    )

    def boom(*a, **kw):
        raise RuntimeError("simulated network failure")

    monkeypatch.setattr(
        "src.finance.__main__.fetch_reports_list",
        lambda params: [{
            "reportId": "1", "url": "u", "report_type": "Quarterly",
            "filed_date": "2026-04-10", "period_label": "Q1 2026", "is_amended": False,
        }],
    )
    monkeypatch.setattr("src.finance.__main__.fetch_html", boom)
    monkeypatch.setattr("src.finance.__main__.make_playwright_fetcher", lambda: boom)
    rc = main(["--max-failure-rate", "0.2"])
    assert rc == 2
    assert out_path.exists()


def test_full_run_returns_2_when_roster_empty(monkeypatch):
    """Empty roster (no Dem matches) returns exit code 2 — nothing to scrape."""
    from src.finance.__main__ import main

    monkeypatch.setattr(
        "src.finance.__main__.fetch_coverage_candidates",
        lambda **kw: {"lastUpdated": "x", "house": {}, "senate": {}},
    )
    monkeypatch.setattr(
        "src.finance.__main__.make_playwright_fetcher",
        lambda: (lambda url: ""),
    )
    rc = main([])
    assert rc == 2

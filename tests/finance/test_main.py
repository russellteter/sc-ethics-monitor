"""Tests for :mod:`src.finance.__main__` CLI entry point.

These mock the heavy dependencies (Playwright, network) and exercise the
control-flow branches: arg parsing, dry-run, missing VREMS state, success
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


def test_dry_run_returns_zero_when_vrems_missing(monkeypatch, tmp_path, capsys):
    """When VREMS state is missing, --dry-run still exits 0 with a clear message."""
    from src.finance import config
    from src.finance.__main__ import main

    monkeypatch.setattr(config, "VREMS_STATE_PATH", tmp_path / "missing.json")
    rc = main(["--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "VREMS state missing" in out


def test_non_dry_run_returns_2_when_vrems_missing(monkeypatch, tmp_path):
    """A real run without VREMS state returns 2 (no work to do)."""
    from src.finance import config
    from src.finance.__main__ import main

    monkeypatch.setattr(config, "VREMS_STATE_PATH", tmp_path / "missing.json")
    assert main([]) == 2


def test_dry_run_loads_roster_and_returns_zero(monkeypatch, tmp_path, capsys):
    """When VREMS state exists, --dry-run loads the roster and exits 0."""
    from src.finance import config
    from src.finance.__main__ import main

    vrems = tmp_path / "vrems.json"
    vrems.write_text(
        json.dumps(
            {"seen_candidate_keys": ["bauer|heather|SC House of Representatives|75"]}
        )
    )
    monkeypatch.setattr(config, "VREMS_STATE_PATH", vrems)
    monkeypatch.setattr(
        "src.finance.__main__.load_party_overrides",
        lambda: {"bauer|heather": "D"},
    )
    rc = main(["--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "roster size: 1 Dem House candidates" in out


def test_full_run_writes_artifact(monkeypatch, tmp_path, capsys):
    """Happy-path full run: produces a populated house_finance.json."""
    from src.finance import config
    from src.finance.__main__ import main
    from src.finance.parser import ReportNumbers
    from src.finance.resolver import UrlParams

    vrems = tmp_path / "vrems.json"
    vrems.write_text(
        json.dumps(
            {"seen_candidate_keys": ["bauer|heather|SC House of Representatives|75"]}
        )
    )
    out_path = tmp_path / "house_finance.json"
    cache_path = tmp_path / "cache.json"
    cache_path.write_text("{}")
    ethics = tmp_path / "ethics.json"
    ethics.write_text("{}")

    monkeypatch.setattr(config, "VREMS_STATE_PATH", vrems)
    monkeypatch.setattr(config, "HOUSE_FINANCE_PATH", out_path)
    monkeypatch.setattr(config, "PERSONID_CACHE_PATH", cache_path)
    monkeypatch.setattr(config, "ETHICS_STATE_PATH", ethics)
    monkeypatch.setattr(
        "src.finance.__main__.load_party_overrides",
        lambda: {"bauer|heather": "D"},
    )

    # Stub out the network/browser layer.
    monkeypatch.setattr(
        "src.finance.__main__.search_personId",
        lambda name, district: UrlParams("1", "2", "3"),
    )
    monkeypatch.setattr(
        "src.finance.__main__.fetch_reports_list",
        lambda params: [
            {
                "reportId": "418208",
                "url": "https://example.com/r/418208",
                "report_type": "Quarterly",
                "filed_date": "2026-04-10",
                "period_label": "Q1 2026",
                "is_amended": False,
            }
        ],
    )
    monkeypatch.setattr(
        "src.finance.__main__.fetch_html",
        lambda url, **kw: "<html>Cash Contributions Total Campaign Funds</html>",
    )
    monkeypatch.setattr(
        "src.finance.__main__.parse_report_detail",
        lambda html: ReportNumbers(32806.90, 89372.11, 68448.57),
    )
    # Avoid spinning up real Playwright.
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
    """Failure-rate exceeded → exit code 2 (artifact still written)."""
    from src.finance import config
    from src.finance.__main__ import main
    from src.finance.resolver import UrlParams

    vrems = tmp_path / "vrems.json"
    vrems.write_text(
        json.dumps(
            {
                "seen_candidate_keys": [
                    f"x{i}|cand|SC House of Representatives|{i + 1}"
                    for i in range(5)
                ]
            }
        )
    )
    out_path = tmp_path / "house_finance.json"
    cache_path = tmp_path / "cache.json"
    cache_path.write_text("{}")
    ethics = tmp_path / "ethics.json"
    ethics.write_text("{}")

    monkeypatch.setattr(config, "VREMS_STATE_PATH", vrems)
    monkeypatch.setattr(config, "HOUSE_FINANCE_PATH", out_path)
    monkeypatch.setattr(config, "PERSONID_CACHE_PATH", cache_path)
    monkeypatch.setattr(config, "ETHICS_STATE_PATH", ethics)
    monkeypatch.setattr(
        "src.finance.__main__.load_party_overrides",
        lambda: {f"x{i}|cand": "D" for i in range(5)},
    )

    def boom(*a, **kw):
        raise RuntimeError("simulated network failure")

    monkeypatch.setattr(
        "src.finance.__main__.search_personId",
        lambda name, district: UrlParams("1", "2", "3"),
    )
    monkeypatch.setattr(
        "src.finance.__main__.fetch_reports_list",
        lambda params: [
            {
                "reportId": "1",
                "url": "u",
                "report_type": "Quarterly",
                "filed_date": "2026-04-10",
                "period_label": "Q1 2026",
                "is_amended": False,
            }
        ],
    )
    monkeypatch.setattr("src.finance.__main__.fetch_html", boom)
    monkeypatch.setattr("src.finance.__main__.make_playwright_fetcher", lambda: boom)
    rc = main(["--max-failure-rate", "0.2"])
    assert rc == 2
    # Artifact still written before the abort.
    assert out_path.exists()


def test_full_run_returns_2_when_roster_empty(monkeypatch, tmp_path):
    """Empty roster (no Dem matches) returns exit code 2 — nothing to scrape."""
    from src.finance import config
    from src.finance.__main__ import main

    vrems = tmp_path / "vrems.json"
    vrems.write_text(json.dumps({"seen_candidate_keys": []}))
    monkeypatch.setattr(config, "VREMS_STATE_PATH", vrems)
    monkeypatch.setattr("src.finance.__main__.load_party_overrides", lambda: {})
    monkeypatch.setattr(
        "src.finance.__main__.make_playwright_fetcher",
        lambda: (lambda url: ""),
    )
    rc = main([])
    assert rc == 2

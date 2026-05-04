"""Tests for :mod:`src.finance.party_loader`."""
import json

from src.finance.party_loader import load_party_overrides


def test_returns_empty_when_file_missing(tmp_path):
    assert load_party_overrides(tmp_path / "nope.json") == {}


def test_returns_empty_when_file_blank(tmp_path):
    p = tmp_path / "state.json"
    p.write_text("")
    assert load_party_overrides(p) == {}


def test_returns_empty_on_malformed_json(tmp_path):
    p = tmp_path / "state.json"
    p.write_text("not json {")
    assert load_party_overrides(p) == {}


def test_emits_only_records_with_party_tag_list_shape(tmp_path):
    """Fixture-style state: `reports_with_metadata` is a list."""
    p = tmp_path / "state.json"
    p.write_text(
        json.dumps(
            {
                "reports_with_metadata": [
                    {"candidate": "Bauer, Heather", "detected_party": "D"},
                    {"candidate": "Smith, Alice"},  # no party — skipped
                    {"candidate": "Doe, John", "final_party": "R"},
                ]
            }
        )
    )
    overrides = load_party_overrides(p)
    assert overrides == {"bauer|heather": "D", "doe|john": "R"}


def test_emits_only_records_with_party_tag_dict_shape(tmp_path):
    """Live-state shape: `reports_with_metadata` is a dict keyed by reportId, with `candidate_name`."""
    p = tmp_path / "state.json"
    p.write_text(
        json.dumps(
            {
                "reports_with_metadata": {
                    "417093": {
                        "candidate_name": "Bauer, Heather",
                        "detected_party": "D",
                    },
                    "416493": {
                        "candidate_name": "Smith, Alice",  # no party
                    },
                    "416460": {
                        "candidate_name": "Jones, Bob",
                        "final_party": "R",
                    },
                }
            }
        )
    )
    overrides = load_party_overrides(p)
    assert overrides == {"bauer|heather": "D", "jones|bob": "R"}


def test_skips_records_without_comma_in_name(tmp_path):
    p = tmp_path / "state.json"
    p.write_text(
        json.dumps(
            {
                "reports_with_metadata": [
                    {"candidate": "Heather Bauer", "detected_party": "D"},  # no comma
                    {"candidate": "Bauer, Heather", "detected_party": "D"},
                ]
            }
        )
    )
    overrides = load_party_overrides(p)
    assert "bauer|heather" in overrides
    assert len(overrides) == 1


def test_skips_blank_first_or_last(tmp_path):
    p = tmp_path / "state.json"
    p.write_text(
        json.dumps(
            {
                "reports_with_metadata": [
                    {"candidate": ", Heather", "detected_party": "D"},
                    {"candidate": "Bauer, ", "detected_party": "D"},
                    {"candidate": "Bauer, Heather", "detected_party": "D"},
                ]
            }
        )
    )
    assert load_party_overrides(p) == {"bauer|heather": "D"}


def test_skips_non_dict_records(tmp_path):
    """A non-dict entry in the records iterable is silently skipped."""
    p = tmp_path / "state.json"
    p.write_text(
        json.dumps(
            {
                "reports_with_metadata": [
                    "garbage string",
                    None,
                    {"candidate": "Bauer, Heather", "detected_party": "D"},
                ]
            }
        )
    )
    assert load_party_overrides(p) == {"bauer|heather": "D"}


def test_final_party_wins_over_detected(tmp_path):
    """If both `final_party` and `detected_party` are present, final wins."""
    p = tmp_path / "state.json"
    p.write_text(
        json.dumps(
            {
                "reports_with_metadata": [
                    {
                        "candidate": "Bauer, Heather",
                        "detected_party": "I",
                        "final_party": "D",
                    }
                ]
            }
        )
    )
    assert load_party_overrides(p) == {"bauer|heather": "D"}

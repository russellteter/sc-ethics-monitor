"""Tests for the party_detect cache wrapper."""
import json

from src.finance.party_detect import detect_party_with_cache


def test_cache_hit_skips_detector(tmp_path, mocker):
    cache_file = tmp_path / "party_cache.json"
    cache_file.write_text(json.dumps({
        "bauer|heather|75": {
            "party": "D",
            "confidence": "HIGH",
            "source": "incumbent",
            "detected_at": "2026-01-01T00:00:00Z",
        }
    }))
    detector_mock = mocker.MagicMock()
    party = detect_party_with_cache(
        cache_path=cache_file,
        cache_key="bauer|heather|75",
        candidate_name="Heather Bauer",
        district=75,
        detector=detector_mock,
    )
    assert party == "D"
    detector_mock.assert_not_called()


def test_cache_miss_calls_detector_and_persists(tmp_path, mocker):
    cache_file = tmp_path / "party_cache.json"
    cache_file.write_text("{}")
    detector_mock = mocker.MagicMock(return_value=("D", "HIGH", "ballotpedia"))
    party = detect_party_with_cache(
        cache_path=cache_file,
        cache_key="bauer|heather|75",
        candidate_name="Heather Bauer",
        district=75,
        detector=detector_mock,
    )
    assert party == "D"
    detector_mock.assert_called_once_with("Heather Bauer", 75)
    cached = json.loads(cache_file.read_text())
    assert cached["bauer|heather|75"]["party"] == "D"
    assert cached["bauer|heather|75"]["confidence"] == "HIGH"
    assert cached["bauer|heather|75"]["source"] == "ballotpedia"
    assert "detected_at" in cached["bauer|heather|75"]


def test_low_confidence_returns_party_but_flagged(tmp_path, mocker):
    cache_file = tmp_path / "party_cache.json"
    cache_file.write_text("{}")
    detector_mock = mocker.MagicMock(return_value=("D", "LOW", "name-heuristic"))
    party = detect_party_with_cache(
        cache_path=cache_file,
        cache_key="x|y|1",
        candidate_name="X Y",
        district=1,
        detector=detector_mock,
    )
    assert party == "D"
    cached = json.loads(cache_file.read_text())
    assert cached["x|y|1"]["confidence"] == "LOW"


def test_detector_raises_returns_unknown(tmp_path, mocker):
    cache_file = tmp_path / "party_cache.json"
    cache_file.write_text("{}")
    detector_mock = mocker.MagicMock(side_effect=RuntimeError("boom"))
    party = detect_party_with_cache(
        cache_path=cache_file,
        cache_key="x|y|1",
        candidate_name="X Y",
        district=1,
        detector=detector_mock,
    )
    assert party == "?"
    cached = json.loads(cache_file.read_text())
    assert cached["x|y|1"]["party"] == "?"
    assert "error" in cached["x|y|1"]


def test_missing_cache_file_treated_as_empty(tmp_path, mocker):
    cache_file = tmp_path / "does_not_exist.json"
    detector_mock = mocker.MagicMock(return_value=("R", "HIGH", "incumbent"))
    party = detect_party_with_cache(
        cache_path=cache_file,
        cache_key="a|b|2",
        candidate_name="A B",
        district=2,
        detector=detector_mock,
    )
    assert party == "R"
    assert cache_file.exists()
    assert json.loads(cache_file.read_text())["a|b|2"]["party"] == "R"

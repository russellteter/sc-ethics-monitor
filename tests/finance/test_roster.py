import json

from src.finance.roster import Candidate, load_dem_house_roster


def test_filters_to_dem_house_only(vrems_state_path):
    roster = load_dem_house_roster(
        vrems_state_path,
        party_overrides={
            "bauer|heather": "D",
            "pendarvis|marvin": "D",
            "kirby|roger": "D",
            "jones|bob": "R",
        },
    )
    names = sorted(c.name for c in roster)
    assert names == ["Heather Bauer", "Marvin Pendarvis", "Roger Kirby"]
    assert all(c.party == "D" for c in roster)
    assert all("House" in c.office for c in roster)


def test_returns_candidate_objects_with_district(vrems_state_path):
    roster = load_dem_house_roster(
        vrems_state_path,
        party_overrides={"bauer|heather": "D"},
    )
    bauer = next(c for c in roster if c.name == "Heather Bauer")
    assert isinstance(bauer, Candidate)
    assert bauer.district == 75
    assert bauer.id == "bauer-heather-75"


def test_excludes_senate(vrems_state_path):
    roster = load_dem_house_roster(
        vrems_state_path,
        party_overrides={"smith|alice": "D"},
    )
    assert all("Senate" not in c.office for c in roster)
    assert all("smith" not in c.name.lower() for c in roster)


def test_skips_non_dem_party(vrems_state_path):
    roster = load_dem_house_roster(
        vrems_state_path,
        party_overrides={"jones|bob": "R", "bauer|heather": "I"},
    )
    assert roster == []


def test_handles_missing_overrides(vrems_state_path):
    """Candidates without a party override are skipped."""
    roster = load_dem_house_roster(vrems_state_path, party_overrides=None)
    assert roster == []


def test_matches_vrems_state_house_format():
    from src.finance.roster import _is_state_house
    assert _is_state_house("state house of representatives, district 92")
    assert _is_state_house("State House of Representatives, District 075")


def test_does_not_match_senate():
    from src.finance.roster import _is_state_house
    assert not _is_state_house("state senate, district 10")


def test_skips_malformed_keys(tmp_path):
    """Keys that don't have 4 pipe-separated parts or non-int districts are skipped."""
    import json

    bad = tmp_path / "vrems.json"
    bad.write_text(
        json.dumps(
            {
                "seen_candidate_keys": [
                    "too|few|parts",
                    "bauer|heather|SC House of Representatives|notanint",
                    "bauer|heather|SC House of Representatives|75",
                ]
            }
        )
    )
    roster = load_dem_house_roster(bad, party_overrides={"bauer|heather": "D"})
    assert len(roster) == 1
    assert roster[0].district == 75


def test_roster_uses_party_detect_when_no_overrides(tmp_path, mocker):
    """The detection-based roster keeps Dems detected via party_detect cache."""
    from src.finance.roster import load_dem_house_roster_with_detection

    vrems = tmp_path / "vrems.json"
    vrems.write_text(
        json.dumps(
            {
                "seen_candidate_keys": [
                    "bauer|heather|state house of representatives, district 75|075",
                    "smith|john|state house of representatives, district 22|022",
                ]
            }
        )
    )
    cache = tmp_path / "party_cache.json"
    cache.write_text("{}")

    def fake_detect(*args, **kwargs):
        if "bauer" in kwargs["cache_key"]:
            return "D"
        return "R"

    mocker.patch("src.finance.roster._detect_party", side_effect=fake_detect)

    roster = load_dem_house_roster_with_detection(
        vrems_state_path=vrems, party_cache_path=cache
    )
    names = sorted(c.name for c in roster)
    assert names == ["Heather Bauer"]


def test_roster_with_detection_skips_senate(tmp_path, mocker):
    from src.finance.roster import load_dem_house_roster_with_detection

    vrems = tmp_path / "vrems.json"
    vrems.write_text(
        json.dumps(
            {
                "seen_candidate_keys": [
                    "alpha|alice|state senate, district 5|005",
                ]
            }
        )
    )
    cache = tmp_path / "party_cache.json"
    cache.write_text("{}")
    detect_spy = mocker.patch(
        "src.finance.roster._detect_party", return_value="D"
    )

    roster = load_dem_house_roster_with_detection(
        vrems_state_path=vrems, party_cache_path=cache
    )
    assert roster == []
    detect_spy.assert_not_called()

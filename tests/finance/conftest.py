"""Shared fixtures for finance tests."""
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def vrems_state_path():
    return FIXTURES / "sample_vrems_state.json"


@pytest.fixture
def ethics_state_path():
    return FIXTURES / "sample_ethics_state.json"


@pytest.fixture
def personid_cache_path():
    return FIXTURES / "sample_personid_cache.json"


@pytest.fixture
def heather_bauer_html():
    return (FIXTURES / "heather_bauer_418208.html").read_text()

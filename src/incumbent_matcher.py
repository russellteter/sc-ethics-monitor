"""
Incumbent Matcher - Fuzzy name matching against incumbents.json.

Matches candidate names from ethics filings against known incumbents
to determine party affiliation with HIGH confidence.
"""

import re
from dataclasses import dataclass
from typing import Optional

try:
    from fuzzywuzzy import fuzz
except ImportError:
    # Fallback to simple matching if fuzzywuzzy not available
    fuzz = None

from config import (
    load_incumbents,
    FUZZY_MATCH_THRESHOLD,
    get_district_number,
    is_house_district,
    is_senate_district,
    CONFIDENCE_LEVELS
)


@dataclass
class IncumbentMatch:
    """Result of incumbent matching."""
    matched: bool
    incumbent_name: Optional[str] = None
    party: Optional[str] = None
    confidence: str = CONFIDENCE_LEVELS["UNKNOWN"]
    district_id: Optional[str] = None
    match_score: int = 0
    evidence_url: Optional[str] = None


def normalize_name(name: str) -> str:
    """
    Normalize a name for comparison.

    - Convert to lowercase
    - Remove titles (Jr., III, etc.)
    - Remove middle initials
    - Remove quotes/nicknames
    - Strip extra whitespace
    """
    if not name:
        return ""

    # Lowercase
    name = name.lower()

    # Remove HTML entities
    name = name.replace("&quot;", "").replace("&#39;", "")

    # Remove nicknames in quotes
    name = re.sub(r'"[^"]*"', '', name)
    name = re.sub(r"'[^']*'", '', name)

    # Remove suffixes
    suffixes = [
        r'\biv\b', r'\biii\b', r'\bii\b', r'\bjr\.?\b', r'\bsr\.?\b',
        r'\bph\.?d\.?\b', r'\bm\.?d\.?\b', r'\besq\.?\b'
    ]
    for suffix in suffixes:
        name = re.sub(suffix, '', name, flags=re.IGNORECASE)

    # Remove single initials (middle names)
    name = re.sub(r'\b[a-z]\.\s*', '', name)

    # Remove periods and commas
    name = re.sub(r'[.,]', '', name)

    # Normalize whitespace
    name = ' '.join(name.split())

    return name.strip()


def extract_last_first(name: str) -> tuple[str, str]:
    """
    Extract last name and first name from a name string.

    Handles formats:
    - "Last, First" (ethics filing format)
    - "First Last" (standard format)
    """
    name = normalize_name(name)

    if ',' in name:
        # "Last, First" format
        parts = name.split(',', 1)
        last = parts[0].strip()
        first = parts[1].strip() if len(parts) > 1 else ""
    else:
        # "First Last" format
        parts = name.split()
        if len(parts) >= 2:
            first = parts[0]
            last = parts[-1]
        elif len(parts) == 1:
            last = parts[0]
            first = ""
        else:
            last = ""
            first = ""

    return last, first


def fuzzy_name_match(name1: str, name2: str) -> int:
    """
    Calculate fuzzy match score between two names.

    Returns:
        Score from 0-100, where 100 is exact match
    """
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)

    if not n1 or not n2:
        return 0

    # Exact match after normalization
    if n1 == n2:
        return 100

    if fuzz:
        # Use fuzzywuzzy for sophisticated matching
        # token_sort_ratio handles reordering (First Last vs Last First)
        return fuzz.token_sort_ratio(n1, n2)
    else:
        # Simple fallback: check if names contain same words
        words1 = set(n1.split())
        words2 = set(n2.split())

        if not words1 or not words2:
            return 0

        intersection = words1 & words2
        union = words1 | words2

        # Jaccard similarity as percentage
        return int((len(intersection) / len(union)) * 100)


def match_against_incumbents(
    candidate_name: str,
    office: str,
    incumbents: Optional[dict] = None
) -> IncumbentMatch:
    """
    Match a candidate name against known incumbents.

    Args:
        candidate_name: Name from ethics filing (e.g., "Morgan, Tyler A")
        office: Office string (e.g., "SC House of Representatives District 91")
        incumbents: Optional incumbents dict, will load if not provided

    Returns:
        IncumbentMatch with match results
    """
    if incumbents is None:
        incumbents = load_incumbents()

    if not candidate_name or not office:
        return IncumbentMatch(matched=False)

    # Determine chamber and district
    district_num = get_district_number(office)
    if district_num is None:
        return IncumbentMatch(matched=False)

    if is_house_district(office):
        chamber = "house"
        district_id = f"H{district_num:03d}"
    elif is_senate_district(office):
        chamber = "senate"
        district_id = f"S{district_num:03d}"
    else:
        return IncumbentMatch(matched=False)

    # Get incumbent for this district
    chamber_data = incumbents.get(chamber, {})
    incumbent_data = chamber_data.get(str(district_num))

    if not incumbent_data:
        # No incumbent in this district (or data not available)
        return IncumbentMatch(matched=False, district_id=district_id)

    incumbent_name = incumbent_data.get("name", "")
    incumbent_party = incumbent_data.get("party", "")
    incumbent_url = incumbent_data.get("url", "")

    # Calculate match score
    match_score = fuzzy_name_match(candidate_name, incumbent_name)

    if match_score >= FUZZY_MATCH_THRESHOLD:
        # High confidence match - candidate is the incumbent
        party = "D" if incumbent_party.lower().startswith("dem") else "R"

        return IncumbentMatch(
            matched=True,
            incumbent_name=incumbent_name,
            party=party,
            confidence=CONFIDENCE_LEVELS["HIGH"],
            district_id=district_id,
            match_score=match_score,
            evidence_url=incumbent_url
        )
    else:
        # Not a match - candidate is a challenger
        return IncumbentMatch(
            matched=False,
            incumbent_name=incumbent_name,
            district_id=district_id,
            match_score=match_score
        )


def find_best_incumbent_match(
    candidate_name: str,
    incumbents: Optional[dict] = None
) -> IncumbentMatch:
    """
    Search all incumbents to find the best match for a candidate name.

    Useful when district is unknown or for validation.

    Args:
        candidate_name: Name to search for
        incumbents: Optional incumbents dict

    Returns:
        Best IncumbentMatch found
    """
    if incumbents is None:
        incumbents = load_incumbents()

    best_match = IncumbentMatch(matched=False)
    best_score = 0

    for chamber in ["house", "senate"]:
        chamber_data = incumbents.get(chamber, {})

        for district_num, incumbent_data in chamber_data.items():
            incumbent_name = incumbent_data.get("name", "")
            match_score = fuzzy_name_match(candidate_name, incumbent_name)

            if match_score > best_score:
                best_score = match_score
                incumbent_party = incumbent_data.get("party", "")
                party = "D" if incumbent_party.lower().startswith("dem") else "R"

                if chamber == "house":
                    district_id = f"H{int(district_num):03d}"
                else:
                    district_id = f"S{int(district_num):03d}"

                best_match = IncumbentMatch(
                    matched=match_score >= FUZZY_MATCH_THRESHOLD,
                    incumbent_name=incumbent_name,
                    party=party if match_score >= FUZZY_MATCH_THRESHOLD else None,
                    confidence=CONFIDENCE_LEVELS["HIGH"] if match_score >= FUZZY_MATCH_THRESHOLD else CONFIDENCE_LEVELS["UNKNOWN"],
                    district_id=district_id,
                    match_score=match_score,
                    evidence_url=incumbent_data.get("url")
                )

    return best_match


def get_incumbent_for_district(
    district_id: str,
    incumbents: Optional[dict] = None
) -> Optional[dict]:
    """
    Get incumbent data for a specific district.

    Args:
        district_id: District ID like "H091" or "S015"
        incumbents: Optional incumbents dict

    Returns:
        Incumbent data dict or None
    """
    if incumbents is None:
        incumbents = load_incumbents()

    if not district_id or len(district_id) < 2:
        return None

    chamber = "house" if district_id[0].upper() == "H" else "senate"
    district_num = district_id[1:].lstrip("0") or "0"

    chamber_data = incumbents.get(chamber, {})
    return chamber_data.get(district_num)


def is_candidate_incumbent(
    candidate_name: str,
    office: str,
    incumbents: Optional[dict] = None
) -> bool:
    """
    Quick check if a candidate appears to be the incumbent.

    Args:
        candidate_name: Name from ethics filing
        office: Office string

    Returns:
        True if candidate matches incumbent for that district
    """
    result = match_against_incumbents(candidate_name, office, incumbents)
    return result.matched


if __name__ == "__main__":
    # Test the matcher
    test_cases = [
        ("Morgan, Tyler A", "SC House of Representatives District 91"),
        ("Hosey, Lonnie", "SC House of Representatives District 91"),
        ("Burns, James R", "SC Senate District 15"),
        ("Unknown Person", "SC House of Representatives District 1"),
    ]

    print("Testing Incumbent Matcher")
    print("=" * 60)

    for name, office in test_cases:
        result = match_against_incumbents(name, office)
        print(f"\nCandidate: {name}")
        print(f"Office: {office}")
        print(f"Matched: {result.matched}")
        if result.matched:
            print(f"  Party: {result.party}")
            print(f"  Confidence: {result.confidence}")
            print(f"  Score: {result.match_score}")
        elif result.incumbent_name:
            print(f"  Incumbent: {result.incumbent_name} (score: {result.match_score})")

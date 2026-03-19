"""
Ballotpedia Source - Search Ballotpedia for candidate information.

Ballotpedia is a comprehensive political encyclopedia that typically includes
party affiliation in candidate infoboxes.
"""

import re
from typing import Optional
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import FIRECRAWL_API_KEY, BALLOTPEDIA_BASE_URL, CONFIDENCE_LEVELS


def search_ballotpedia(
    candidate_name: str,
    office: str
) -> Optional[dict]:
    """
    Search Ballotpedia for candidate party information.

    Args:
        candidate_name: Candidate name
        office: Office string (e.g., "SC House of Representatives District 91")

    Returns:
        Dict with party, confidence, evidence_url, evidence_text or None
    """
    if not FIRECRAWL_API_KEY:
        return None

    try:
        from firecrawl import FirecrawlApp
        app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

        # Construct search query
        # Format name for better search (Last, First -> First Last)
        name_parts = candidate_name.split(',')
        if len(name_parts) >= 2:
            search_name = f"{name_parts[1].strip()} {name_parts[0].strip()}"
        else:
            search_name = candidate_name

        query = f'site:ballotpedia.org "{search_name}" South Carolina'

        try:
            results = app.search(query, limit=3)

            for result in results.get('data', []):
                url = result.get('url', '')

                # Only process Ballotpedia URLs
                if 'ballotpedia.org' not in url.lower():
                    continue

                content = result.get('markdown', '') or result.get('content', '')
                if not content:
                    continue

                # Parse content for party affiliation
                party_info = _parse_ballotpedia_content(content, url, candidate_name)
                if party_info:
                    return party_info

        except Exception as e:
            print(f"Ballotpedia search error: {e}")

    except ImportError:
        pass

    return None


def _parse_ballotpedia_content(
    content: str,
    url: str,
    candidate_name: str
) -> Optional[dict]:
    """
    Parse Ballotpedia page content for party information.

    Looks for:
    - Party field in infobox
    - "(D)" or "(R)" after name
    - "Democrat" or "Republican" in context
    """
    if not content:
        return None

    content_lower = content.lower()

    # Check if candidate name is mentioned
    name_parts = candidate_name.lower().split(',')[0].split()
    last_name = name_parts[-1] if name_parts else ""

    if last_name and last_name not in content_lower:
        return None

    # Look for explicit party indicators
    # Ballotpedia often has "Party: Democratic" or "Party: Republican"
    party_patterns = [
        (r'party[:\s]+democratic', 'D'),
        (r'party[:\s]+republican', 'R'),
        (r'party[:\s]+democrat(?!ic)', 'D'),
        (r'\(d\)(?:\s*-|\s*,|\s*$)', 'D'),
        (r'\(r\)(?:\s*-|\s*,|\s*$)', 'R'),
        (r'\bdemocratic\s+party\b', 'D'),
        (r'\brepublican\s+party\b', 'R'),
        (r'\bdemocratic\s+(?:candidate|nominee|primary)\b', 'D'),
        (r'\brepublican\s+(?:candidate|nominee|primary)\b', 'R'),
    ]

    for pattern, party in party_patterns:
        if re.search(pattern, content_lower):
            # Extract relevant text snippet
            match = re.search(pattern, content_lower)
            if match:
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 100)
                snippet = content[start:end].strip()

                return {
                    "party": party,
                    "confidence": CONFIDENCE_LEVELS["MEDIUM"],
                    "evidence_url": url,
                    "evidence_text": snippet,
                    "source": "ballotpedia"
                }

    return None


def get_ballotpedia_url(candidate_name: str, state: str = "South_Carolina") -> str:
    """
    Generate a likely Ballotpedia URL for a candidate.

    Args:
        candidate_name: Candidate name
        state: State name (underscored)

    Returns:
        Formatted Ballotpedia URL
    """
    # Format name for URL
    name_parts = candidate_name.split(',')
    if len(name_parts) >= 2:
        formatted_name = f"{name_parts[1].strip()}_{name_parts[0].strip()}"
    else:
        formatted_name = candidate_name

    # Clean up name for URL
    formatted_name = formatted_name.replace(" ", "_")
    formatted_name = re.sub(r'[^\w_]', '', formatted_name)

    return f"{BALLOTPEDIA_BASE_URL}/{formatted_name}"


if __name__ == "__main__":
    # Test the module
    print("Testing Ballotpedia Search")
    print("=" * 60)

    test_candidates = [
        ("Hosey, Lonnie", "SC House of Representatives District 91"),
        ("Burns, James R", "SC Senate District 15"),
    ]

    for name, office in test_candidates:
        print(f"\nSearching: {name}")
        result = search_ballotpedia(name, office)
        if result:
            print(f"  Party: {result.get('party')}")
            print(f"  Confidence: {result.get('confidence')}")
            print(f"  URL: {result.get('evidence_url')}")
        else:
            print("  No result found")

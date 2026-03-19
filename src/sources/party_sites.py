"""
Party Websites Source - Search SCDP and SCGOP official websites.

Searches the South Carolina Democratic Party (scdp.org) and
South Carolina Republican Party (scgop.com) for candidate endorsements
and official candidate listings.
"""

import re
from typing import Optional
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import FIRECRAWL_API_KEY, SCDP_URL, SCGOP_URL, CONFIDENCE_LEVELS


def search_party_websites(
    candidate_name: str,
    office: str
) -> Optional[dict]:
    """
    Search party websites for candidate information.

    Searches both SCDP and SCGOP websites.

    Args:
        candidate_name: Candidate name
        office: Office string

    Returns:
        Dict with party, confidence, evidence_url, evidence_text or None
    """
    if not FIRECRAWL_API_KEY:
        return None

    # Try Democratic Party first
    dem_result = _search_scdp(candidate_name, office)
    if dem_result:
        return dem_result

    # Try Republican Party
    rep_result = _search_scgop(candidate_name, office)
    if rep_result:
        return rep_result

    return None


def _search_scdp(candidate_name: str, office: str) -> Optional[dict]:
    """Search SCDP website for candidate."""
    try:
        from firecrawl import FirecrawlApp
        app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

        # Format name for search
        name_parts = candidate_name.split(',')
        if len(name_parts) >= 2:
            search_name = f"{name_parts[1].strip()} {name_parts[0].strip()}"
        else:
            search_name = candidate_name

        query = f'site:scdp.org "{search_name}"'

        try:
            results = app.search(query, limit=3)

            for result in results.get('data', []):
                url = result.get('url', '')

                if 'scdp.org' not in url.lower():
                    continue

                content = result.get('markdown', '') or result.get('content', '')
                if not content:
                    continue

                # Verify name is mentioned
                last_name = candidate_name.split(',')[0].strip().lower()
                if last_name not in content.lower():
                    continue

                # Found on SCDP = Democrat
                snippet = content[:200] + "..." if len(content) > 200 else content

                return {
                    "party": "D",
                    "confidence": CONFIDENCE_LEVELS["HIGH"],
                    "evidence_url": url,
                    "evidence_text": snippet,
                    "source": "scdp_website"
                }

        except Exception as e:
            print(f"SCDP search error: {e}")

    except ImportError:
        pass

    return None


def _search_scgop(candidate_name: str, office: str) -> Optional[dict]:
    """Search SCGOP website for candidate."""
    try:
        from firecrawl import FirecrawlApp
        app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

        # Format name for search
        name_parts = candidate_name.split(',')
        if len(name_parts) >= 2:
            search_name = f"{name_parts[1].strip()} {name_parts[0].strip()}"
        else:
            search_name = candidate_name

        query = f'site:scgop.com "{search_name}"'

        try:
            results = app.search(query, limit=3)

            for result in results.get('data', []):
                url = result.get('url', '')

                if 'scgop.com' not in url.lower():
                    continue

                content = result.get('markdown', '') or result.get('content', '')
                if not content:
                    continue

                # Verify name is mentioned
                last_name = candidate_name.split(',')[0].strip().lower()
                if last_name not in content.lower():
                    continue

                # Found on SCGOP = Republican
                snippet = content[:200] + "..." if len(content) > 200 else content

                return {
                    "party": "R",
                    "confidence": CONFIDENCE_LEVELS["HIGH"],
                    "evidence_url": url,
                    "evidence_text": snippet,
                    "source": "scgop_website"
                }

        except Exception as e:
            print(f"SCGOP search error: {e}")

    except ImportError:
        pass

    return None


def search_party_website_direct(party: str, candidate_name: str) -> Optional[dict]:
    """
    Directly scrape a party website for candidate mentions.

    Args:
        party: "D" or "R"
        candidate_name: Candidate name

    Returns:
        Dict with party confirmation or None
    """
    if not FIRECRAWL_API_KEY:
        return None

    try:
        from firecrawl import FirecrawlApp
        app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

        base_url = SCDP_URL if party == "D" else SCGOP_URL

        # Try to scrape the candidates or endorsed candidates page
        candidate_pages = [
            f"{base_url}/candidates",
            f"{base_url}/our-candidates",
            f"{base_url}/endorsed-candidates",
        ]

        for page_url in candidate_pages:
            try:
                result = app.scrape_url(page_url, params={'formats': ['markdown']})

                content = result.get('markdown', '')
                if not content:
                    continue

                # Check if candidate mentioned
                last_name = candidate_name.split(',')[0].strip().lower()
                if last_name in content.lower():
                    return {
                        "party": party,
                        "confidence": CONFIDENCE_LEVELS["HIGH"],
                        "evidence_url": page_url,
                        "evidence_text": f"Found on {base_url} candidates page",
                        "source": "scdp_direct" if party == "D" else "scgop_direct"
                    }

            except Exception:
                continue

    except ImportError:
        pass

    return None


if __name__ == "__main__":
    # Test the module
    print("Testing Party Website Search")
    print("=" * 60)

    test_candidates = [
        ("Hosey, Lonnie", "SC House of Representatives District 91"),
        ("Burns, James R", "SC Senate District 15"),
    ]

    for name, office in test_candidates:
        print(f"\nSearching: {name}")
        result = search_party_websites(name, office)
        if result:
            print(f"  Party: {result.get('party')}")
            print(f"  Source: {result.get('source')}")
            print(f"  URL: {result.get('evidence_url')}")
        else:
            print("  No result found")

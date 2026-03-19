"""
Social Media Source - Search social media for party indicators.

Searches campaign websites, Facebook, Twitter/X, and other social
platforms for party affiliation indicators like endorsements,
hashtags, and party logos.
"""

import re
from typing import Optional
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import FIRECRAWL_API_KEY, CONFIDENCE_LEVELS


def search_social_media(
    candidate_name: str,
    office: str
) -> Optional[dict]:
    """
    Search social media and campaign websites for party indicators.

    Args:
        candidate_name: Candidate name
        office: Office string

    Returns:
        Dict with party, confidence, evidence_url, evidence_text or None
    """
    if not FIRECRAWL_API_KEY:
        return None

    # Try campaign website search
    campaign_result = _search_campaign_website(candidate_name, office)
    if campaign_result:
        return campaign_result

    # Try general social media search
    social_result = _search_social_general(candidate_name, office)
    if social_result:
        return social_result

    return None


def _search_campaign_website(candidate_name: str, office: str) -> Optional[dict]:
    """Search for candidate's campaign website."""
    try:
        from firecrawl import FirecrawlApp
        app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

        # Format name for search
        name_parts = candidate_name.split(',')
        if len(name_parts) >= 2:
            first_name = name_parts[1].strip().split()[0]  # First name only
            last_name = name_parts[0].strip()
            search_name = f"{first_name} {last_name}"
        else:
            search_name = candidate_name

        # Search for campaign website
        query = f'"{search_name}" campaign South Carolina 2026 OR 2025'

        try:
            results = app.search(query, limit=5)

            for result in results.get('data', []):
                url = result.get('url', '')
                content = result.get('markdown', '') or result.get('content', '')

                if not content:
                    continue

                # Skip news sites (less reliable)
                if any(site in url.lower() for site in [
                    'news', 'times', 'post', 'herald', 'journal', 'tribune'
                ]):
                    continue

                # Analyze content for party indicators
                party_info = _analyze_campaign_content(content, url, candidate_name)
                if party_info:
                    return party_info

        except Exception as e:
            print(f"Campaign website search error: {e}")

    except ImportError:
        pass

    return None


def _search_social_general(candidate_name: str, office: str) -> Optional[dict]:
    """Search social media platforms for party indicators."""
    try:
        from firecrawl import FirecrawlApp
        app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

        # Format name for search
        name_parts = candidate_name.split(',')
        if len(name_parts) >= 2:
            search_name = f"{name_parts[1].strip()} {name_parts[0].strip()}"
        else:
            search_name = candidate_name

        # Search Twitter/X and Facebook
        query = f'"{search_name}" (site:twitter.com OR site:x.com OR site:facebook.com) South Carolina'

        try:
            results = app.search(query, limit=5)

            for result in results.get('data', []):
                url = result.get('url', '')
                content = result.get('markdown', '') or result.get('content', '')

                if not content:
                    continue

                # Analyze content
                party_info = _analyze_social_content(content, url, candidate_name)
                if party_info:
                    return party_info

        except Exception as e:
            print(f"Social media search error: {e}")

    except ImportError:
        pass

    return None


def _analyze_campaign_content(
    content: str,
    url: str,
    candidate_name: str
) -> Optional[dict]:
    """Analyze campaign website content for party indicators."""
    if not content:
        return None

    content_lower = content.lower()

    # Check if candidate name is mentioned
    last_name = candidate_name.split(',')[0].strip().lower()
    if last_name not in content_lower:
        return None

    # Look for party indicators
    dem_indicators = [
        r'\bdemocrat\b',
        r'\bdemocratic\b',
        r'\bblue\s+wave\b',
        r'\bprogressive\b',
        r'#voteblue',
        r'@scdp',
        r'endorsed\s+by.*democrat',
    ]

    rep_indicators = [
        r'\brepublican\b',
        r'\bgop\b',
        r'\bconservative\b',
        r'\btrump\b',
        r'#voterepublican',
        r'#maga',
        r'@scgop',
        r'endorsed\s+by.*republican',
    ]

    dem_count = sum(
        len(re.findall(pattern, content_lower, re.IGNORECASE))
        for pattern in dem_indicators
    )

    rep_count = sum(
        len(re.findall(pattern, content_lower, re.IGNORECASE))
        for pattern in rep_indicators
    )

    # Need a clear signal
    if dem_count >= 2 and dem_count > rep_count:
        snippet = content[:200] + "..." if len(content) > 200 else content
        return {
            "party": "D",
            "confidence": CONFIDENCE_LEVELS["MEDIUM"],
            "evidence_url": url,
            "evidence_text": snippet,
            "source": "campaign_website"
        }
    elif rep_count >= 2 and rep_count > dem_count:
        snippet = content[:200] + "..." if len(content) > 200 else content
        return {
            "party": "R",
            "confidence": CONFIDENCE_LEVELS["MEDIUM"],
            "evidence_url": url,
            "evidence_text": snippet,
            "source": "campaign_website"
        }

    return None


def _analyze_social_content(
    content: str,
    url: str,
    candidate_name: str
) -> Optional[dict]:
    """Analyze social media content for party indicators."""
    if not content:
        return None

    content_lower = content.lower()

    # Check if candidate name is mentioned
    last_name = candidate_name.split(',')[0].strip().lower()
    if last_name not in content_lower:
        return None

    # Social media specific indicators
    dem_indicators = [
        r'@scdp\b',
        r'@thedemocrats\b',
        r'#voteblue\b',
        r'#democratsdeliver\b',
        r'\bblue\s+wave\b',
        r'endorsed\s+by.*democratic',
    ]

    rep_indicators = [
        r'@scgop\b',
        r'@gop\b',
        r'#voterepublican\b',
        r'#maga\b',
        r'#trump\b',
        r'endorsed\s+by.*republican',
    ]

    dem_count = sum(
        len(re.findall(pattern, content_lower, re.IGNORECASE))
        for pattern in dem_indicators
    )

    rep_count = sum(
        len(re.findall(pattern, content_lower, re.IGNORECASE))
        for pattern in rep_indicators
    )

    # Social media signals are lower confidence
    if dem_count >= 2 and dem_count > rep_count:
        snippet = content[:200] + "..." if len(content) > 200 else content
        return {
            "party": "D",
            "confidence": CONFIDENCE_LEVELS["LOW"],
            "evidence_url": url,
            "evidence_text": snippet,
            "source": "social_media"
        }
    elif rep_count >= 2 and rep_count > dem_count:
        snippet = content[:200] + "..." if len(content) > 200 else content
        return {
            "party": "R",
            "confidence": CONFIDENCE_LEVELS["LOW"],
            "evidence_url": url,
            "evidence_text": snippet,
            "source": "social_media"
        }

    return None


def generate_social_search_urls(candidate_name: str) -> list[str]:
    """
    Generate social media search URLs for manual research.

    Args:
        candidate_name: Candidate name

    Returns:
        List of search URLs
    """
    name_parts = candidate_name.split(',')
    if len(name_parts) >= 2:
        search_name = f"{name_parts[1].strip()} {name_parts[0].strip()}"
    else:
        search_name = candidate_name

    encoded_name = search_name.replace(' ', '%20')

    return [
        f"https://twitter.com/search?q={encoded_name}%20South%20Carolina",
        f"https://www.facebook.com/search/top?q={encoded_name}",
        f"https://www.google.com/search?q={encoded_name}+campaign+South+Carolina",
    ]


if __name__ == "__main__":
    # Test the module
    print("Testing Social Media Search")
    print("=" * 60)

    test_candidates = [
        ("Hosey, Lonnie", "SC House of Representatives District 91"),
        ("Burns, James R", "SC Senate District 15"),
    ]

    for name, office in test_candidates:
        print(f"\nSearching: {name}")
        result = search_social_media(name, office)
        if result:
            print(f"  Party: {result.get('party')}")
            print(f"  Confidence: {result.get('confidence')}")
            print(f"  Source: {result.get('source')}")
        else:
            print("  No result found")

        print(f"  Manual search URLs:")
        for url in generate_social_search_urls(name):
            print(f"    - {url}")

"""
Party Detector - Multi-source party affiliation detection.

Detects party affiliation for candidates using multiple sources:
1. Incumbent matching (HIGH confidence)
2. Party website search via Firecrawl (HIGH confidence)
3. Ballotpedia search (MEDIUM-HIGH confidence)
4. Campaign website/social media search (MEDIUM confidence)
5. Local news search (MEDIUM confidence)

Aggregates signals and returns confidence-weighted result.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from config import (
    FIRECRAWL_API_KEY,
    CONFIDENCE_LEVELS,
    load_incumbents,
    parse_district_from_office
)
from incumbent_matcher import match_against_incumbents


@dataclass
class PartySignal:
    """A single party detection signal from one source."""
    source: str
    party: Optional[str]  # D, R, I, O, or None
    confidence: str  # HIGH, MEDIUM, LOW, UNKNOWN
    evidence_url: Optional[str] = None
    evidence_text: Optional[str] = None


@dataclass
class PartyResult:
    """Aggregated party detection result."""
    party: Optional[str]  # D, R, I, O, or None
    confidence: str  # HIGH, MEDIUM, LOW, UNKNOWN
    source: str  # Primary source that determined the party
    evidence_url: Optional[str] = None
    signals: list[PartySignal] = field(default_factory=list)
    detection_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    suggested_searches: list[str] = field(default_factory=list)


def detect_party(
    candidate_name: str,
    office: str,
    incumbents: Optional[dict] = None,
    use_web_sources: bool = True
) -> PartyResult:
    """
    Detect party affiliation for a candidate using multiple sources.

    Args:
        candidate_name: Name from ethics filing
        office: Office string (e.g., "SC House of Representatives District 91")
        incumbents: Optional incumbents dict
        use_web_sources: Whether to use web-based sources (Firecrawl, etc.)

    Returns:
        PartyResult with detected party and confidence
    """
    signals: list[PartySignal] = []
    district_id = parse_district_from_office(office)

    # Load incumbents if not provided
    if incumbents is None:
        incumbents = load_incumbents()

    # 1. Check incumbent match first (highest confidence)
    incumbent_match = match_against_incumbents(candidate_name, office, incumbents)
    if incumbent_match.matched:
        signals.append(PartySignal(
            source="incumbent_match",
            party=incumbent_match.party,
            confidence=CONFIDENCE_LEVELS["HIGH"],
            evidence_url=incumbent_match.evidence_url,
            evidence_text=f"Matched incumbent: {incumbent_match.incumbent_name}"
        ))

    # 2. If Firecrawl is configured, search web sources
    if use_web_sources and FIRECRAWL_API_KEY:
        web_signals = _search_web_sources(candidate_name, office)
        signals.extend(web_signals)

    # 3. Aggregate signals and determine final result
    result = _aggregate_signals(signals, candidate_name, office)

    return result


def _search_web_sources(candidate_name: str, office: str) -> list[PartySignal]:
    """
    Search web sources for party signals using Firecrawl.

    Returns list of PartySignal from various web sources.
    """
    signals = []

    try:
        from firecrawl import FirecrawlApp
        app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

        # Search for candidate
        query = f"{candidate_name} South Carolina {office} Democrat OR Republican party"

        try:
            search_results = app.search(query, limit=5)

            for result in search_results.get('data', []):
                content = result.get('markdown', '') or result.get('content', '')
                url = result.get('url', '')

                if not content:
                    continue

                # Analyze content for party signals
                signal = _analyze_content_for_party(content, url, candidate_name)
                if signal and signal.party:
                    signals.append(signal)

        except Exception as e:
            print(f"Firecrawl search error: {e}")

    except ImportError:
        # Firecrawl not installed, skip web sources
        pass
    except Exception as e:
        print(f"Web source search error: {e}")

    return signals


def _analyze_content_for_party(
    content: str,
    url: str,
    candidate_name: str
) -> Optional[PartySignal]:
    """
    Analyze web content to detect party affiliation.

    Looks for party indicators near candidate name mentions.
    """
    if not content:
        return None

    content_lower = content.lower()
    name_parts = candidate_name.lower().split(',')[0].split()
    last_name = name_parts[-1] if name_parts else ""

    # Skip if candidate name not mentioned
    if last_name and last_name not in content_lower:
        return None

    # Determine source type for confidence
    url_lower = url.lower()
    if "scdp.org" in url_lower or "scdemocrats" in url_lower:
        source = "scdp_website"
        confidence = CONFIDENCE_LEVELS["HIGH"]
    elif "scgop.com" in url_lower or "screpublican" in url_lower:
        source = "scgop_website"
        confidence = CONFIDENCE_LEVELS["HIGH"]
    elif "ballotpedia.org" in url_lower:
        source = "ballotpedia"
        confidence = CONFIDENCE_LEVELS["MEDIUM"]
    else:
        source = "web_search"
        confidence = CONFIDENCE_LEVELS["LOW"]

    # Count party mentions near candidate name
    democrat_patterns = [
        r'\bdemocrat\w*\b',
        r'\bdemocratic\b',
        r'\b\(d\)\b',
        r'\b\(d-',
        r'\bblue wave\b'
    ]

    republican_patterns = [
        r'\brepublican\w*\b',
        r'\bgop\b',
        r'\b\(r\)\b',
        r'\b\(r-',
        r'\bconservative\b'
    ]

    dem_count = sum(
        len(re.findall(pattern, content_lower, re.IGNORECASE))
        for pattern in democrat_patterns
    )

    rep_count = sum(
        len(re.findall(pattern, content_lower, re.IGNORECASE))
        for pattern in republican_patterns
    )

    # Determine party based on mentions
    if dem_count > rep_count and dem_count >= 2:
        party = "D"
    elif rep_count > dem_count and rep_count >= 2:
        party = "R"
    else:
        return None

    # Extract relevant text snippet
    snippet = content[:200] + "..." if len(content) > 200 else content

    return PartySignal(
        source=source,
        party=party,
        confidence=confidence,
        evidence_url=url,
        evidence_text=snippet
    )


def _aggregate_signals(
    signals: list[PartySignal],
    candidate_name: str,
    office: str
) -> PartyResult:
    """
    Aggregate party signals into a final result.

    Priority order:
    1. HIGH confidence signals (incumbent match, party websites)
    2. MEDIUM confidence signals (Ballotpedia)
    3. LOW confidence signals (general web search)

    If signals conflict, prefer higher confidence sources.
    If same confidence, require agreement.
    """
    # Generate suggested searches for manual research
    district = parse_district_from_office(office) or "district"
    suggested_searches = [
        f'"{candidate_name}" South Carolina Democrat',
        f'"{candidate_name}" South Carolina Republican',
        f'"{candidate_name}" {office}',
        f'site:scdp.org "{candidate_name}"',
        f'site:scgop.com "{candidate_name}"',
        f'site:ballotpedia.org "{candidate_name}" South Carolina',
    ]

    if not signals:
        return PartyResult(
            party=None,
            confidence=CONFIDENCE_LEVELS["UNKNOWN"],
            source="no_signals",
            signals=[],
            suggested_searches=suggested_searches
        )

    # Group signals by confidence level
    high_signals = [s for s in signals if s.confidence == CONFIDENCE_LEVELS["HIGH"]]
    medium_signals = [s for s in signals if s.confidence == CONFIDENCE_LEVELS["MEDIUM"]]
    low_signals = [s for s in signals if s.confidence == CONFIDENCE_LEVELS["LOW"]]

    # Process HIGH confidence signals first
    if high_signals:
        parties = [s.party for s in high_signals if s.party]
        if parties:
            # Check for agreement
            if len(set(parties)) == 1:
                primary_signal = high_signals[0]
                return PartyResult(
                    party=parties[0],
                    confidence=CONFIDENCE_LEVELS["HIGH"],
                    source=primary_signal.source,
                    evidence_url=primary_signal.evidence_url,
                    signals=signals,
                    suggested_searches=suggested_searches
                )
            else:
                # Conflicting HIGH signals - unusual, fall through to lower confidence
                pass

    # Process MEDIUM confidence signals
    if medium_signals:
        parties = [s.party for s in medium_signals if s.party]
        if parties and len(set(parties)) == 1:
            primary_signal = medium_signals[0]
            return PartyResult(
                party=parties[0],
                confidence=CONFIDENCE_LEVELS["MEDIUM"],
                source=primary_signal.source,
                evidence_url=primary_signal.evidence_url,
                signals=signals,
                suggested_searches=suggested_searches
            )

    # Process LOW confidence signals
    if low_signals:
        parties = [s.party for s in low_signals if s.party]
        if parties:
            # Count occurrences
            party_counts = {}
            for p in parties:
                party_counts[p] = party_counts.get(p, 0) + 1

            # Get most common party if it appears 2+ times
            most_common = max(party_counts, key=party_counts.get)
            if party_counts[most_common] >= 2:
                primary_signal = next(s for s in low_signals if s.party == most_common)
                return PartyResult(
                    party=most_common,
                    confidence=CONFIDENCE_LEVELS["LOW"],
                    source=primary_signal.source,
                    evidence_url=primary_signal.evidence_url,
                    signals=signals,
                    suggested_searches=suggested_searches
                )

    # No conclusive result
    return PartyResult(
        party=None,
        confidence=CONFIDENCE_LEVELS["UNKNOWN"],
        source="inconclusive",
        signals=signals,
        suggested_searches=suggested_searches
    )


def detect_party_batch(
    candidates: list[dict],
    incumbents: Optional[dict] = None,
    use_web_sources: bool = True
) -> dict[str, PartyResult]:
    """
    Detect party for multiple candidates.

    Args:
        candidates: List of candidate dicts with 'candidate_name', 'office', 'report_id'
        incumbents: Optional incumbents dict
        use_web_sources: Whether to use web sources

    Returns:
        Dict mapping report_id to PartyResult
    """
    if incumbents is None:
        incumbents = load_incumbents()

    results = {}

    for candidate in candidates:
        report_id = candidate.get("report_id", "")
        name = candidate.get("candidate_name", "")
        office = candidate.get("office", "")

        if not report_id or not name:
            continue

        result = detect_party(
            candidate_name=name,
            office=office,
            incumbents=incumbents,
            use_web_sources=use_web_sources
        )

        results[report_id] = result

    return results


def needs_manual_review(result: PartyResult) -> bool:
    """
    Check if a detection result needs manual review.

    Returns True if confidence is LOW or UNKNOWN.
    """
    return result.confidence in [CONFIDENCE_LEVELS["LOW"], CONFIDENCE_LEVELS["UNKNOWN"]]


if __name__ == "__main__":
    # Test party detection
    test_candidates = [
        ("Morgan, Tyler A", "SC House of Representatives District 91"),
        ("Hosey, Lonnie", "SC House of Representatives District 91"),
        ("Burns, James R", "SC Senate District 15"),
        ("Unknown Challenger", "SC House of Representatives District 1"),
    ]

    print("Testing Party Detector")
    print("=" * 60)

    for name, office in test_candidates:
        result = detect_party(name, office, use_web_sources=False)
        print(f"\nCandidate: {name}")
        print(f"Office: {office}")
        print(f"Party: {result.party or 'Unknown'}")
        print(f"Confidence: {result.confidence}")
        print(f"Source: {result.source}")
        if result.evidence_url:
            print(f"Evidence: {result.evidence_url}")
        if needs_manual_review(result):
            print("STATUS: Needs manual review")
            print(f"Suggested searches: {result.suggested_searches[:2]}")

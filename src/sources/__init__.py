"""
Party Detection Sources

Modules for detecting party affiliation from various web sources:
- ballotpedia: Search Ballotpedia for candidate information
- party_sites: Search SCDP and SCGOP official websites
- social_media: Search social media for party indicators
"""

from .ballotpedia import search_ballotpedia
from .party_sites import search_party_websites
from .social_media import search_social_media

__all__ = [
    "search_ballotpedia",
    "search_party_websites",
    "search_social_media"
]

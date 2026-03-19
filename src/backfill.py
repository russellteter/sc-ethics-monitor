#!/usr/bin/env python3
"""
Backfill Script for SC Ethics Report Monitor

Processes existing data in state.json and populates the Google Sheet with
historical candidates and their party affiliations.

Usage:
    python src/backfill.py [--dry-run] [--skip-party-detection]

Options:
    --dry-run               Show what would be done without making changes
    --skip-party-detection  Skip party detection, only sync existing data
    --init-sheets           Initialize Google Sheets structure (create tabs, headers)
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    STATE_FILE,
    load_incumbents,
    parse_district_from_office,
    is_google_sheets_configured,
    is_party_detection_configured,
    CONFIDENCE_LEVELS
)


def log(message: str) -> None:
    """Print timestamped log message."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{timestamp}] {message}")


def load_state() -> dict:
    """Load state from JSON file."""
    if not STATE_FILE.exists():
        log(f"State file not found: {STATE_FILE}")
        return {}

    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        log(f"Error loading state file: {e}")
        return {}


def get_all_candidates(state: dict) -> list[dict]:
    """
    Extract all candidates from state.json.

    Returns list of candidate dicts with standardized fields.
    """
    candidates = []

    # From reports_with_metadata
    reports_metadata = state.get("reports_with_metadata", {})
    for report_id, meta in reports_metadata.items():
        candidates.append({
            "report_id": report_id,
            "candidate_name": meta.get("candidate_name", ""),
            "office": meta.get("office", ""),
            "filed_date": meta.get("filed_date", ""),
            "url": meta.get("url", ""),
            "source": "reports_with_metadata"
        })

    # From historical_2025
    historical = state.get("historical_2025", {}).get("reports", {})
    for report_id, meta in historical.items():
        # Skip if already in reports_with_metadata
        if report_id in reports_metadata:
            continue

        candidates.append({
            "report_id": report_id,
            "candidate_name": meta.get("candidate_name", ""),
            "office": meta.get("office", ""),
            "filed_date": meta.get("filed_date", ""),
            "url": meta.get("url", ""),
            "source": "historical_2025"
        })

    # Deduplicate by candidate name + office
    seen = set()
    unique_candidates = []
    for c in candidates:
        key = (c["candidate_name"], c["office"])
        if key not in seen:
            seen.add(key)
            unique_candidates.append(c)

    return unique_candidates


def detect_party_for_candidate(candidate: dict, incumbents: dict) -> dict:
    """
    Detect party for a single candidate.

    Returns dict with party detection results.
    """
    try:
        from party_detector import detect_party

        result = detect_party(
            candidate["candidate_name"],
            candidate["office"]
        )

        if result:
            return {
                "party": result.party,
                "confidence": result.confidence,
                "source": result.source,
                "evidence_url": result.evidence_url,
                "evidence_text": result.evidence_text
            }
    except ImportError:
        log("Party detector not available")
    except Exception as e:
        log(f"Error detecting party: {e}")

    return {
        "party": None,
        "confidence": CONFIDENCE_LEVELS["UNKNOWN"],
        "source": None,
        "evidence_url": None,
        "evidence_text": None
    }


def backfill_google_sheets(
    candidates: list[dict],
    party_results: dict,
    dry_run: bool = False
) -> bool:
    """
    Backfill Google Sheets with candidate data.

    Args:
        candidates: List of candidate dicts
        party_results: Dict mapping candidate names to party results
        dry_run: If True, only show what would be done

    Returns:
        True if successful
    """
    if dry_run:
        log("DRY RUN - No changes will be made to Google Sheets")
        for c in candidates:
            name = c["candidate_name"]
            party_info = party_results.get(name, {})
            party = party_info.get("party", "?")
            confidence = party_info.get("confidence", "UNKNOWN")
            log(f"  Would add: {name} ({c['office']}) - Party: {party} ({confidence})")
        return True

    try:
        from sheets_sync import SheetsSync

        sheets = SheetsSync()
        if not sheets.connect():
            log("Could not connect to Google Sheets")
            return False

        # Initialize sheet structure
        log("Initializing Google Sheets structure...")
        sheets.initialize_sheets()

        # Populate districts
        log("Populating districts tab...")
        sheets.populate_districts()

        # Add candidates
        log(f"Adding {len(candidates)} candidates...")
        for i, c in enumerate(candidates):
            name = c["candidate_name"]
            party_info = party_results.get(name, {})

            # Parse district
            district_id = parse_district_from_office(c["office"])

            candidate_data = {
                "candidate_name": name,
                "district_id": district_id,
                "office": c["office"],
                "filed_date": c["filed_date"],
                "ethics_report_url": c["url"],
                "detected_party": party_info.get("party"),
                "party_confidence": party_info.get("confidence", "UNKNOWN"),
                "party_evidence_url": party_info.get("evidence_url"),
                "detection_source": party_info.get("source"),
            }

            sheets.add_candidate(candidate_data)

            if (i + 1) % 10 == 0:
                log(f"  Progress: {i + 1}/{len(candidates)} candidates added")

        # Update race analysis
        log("Updating race analysis...")
        sheets.update_race_analysis()

        log("Backfill complete!")
        return True

    except ImportError:
        log("Google Sheets sync not available - install gspread and google-auth")
        return False
    except Exception as e:
        log(f"Error during backfill: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Backfill Google Sheets with existing candidate data"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--skip-party-detection",
        action="store_true",
        help="Skip party detection, only sync existing data"
    )
    parser.add_argument(
        "--init-sheets",
        action="store_true",
        help="Only initialize Google Sheets structure"
    )

    args = parser.parse_args()

    log("=" * 60)
    log("SC Ethics Report Monitor - Backfill Script")
    log("=" * 60)

    # Check configuration
    if not args.dry_run:
        if not is_google_sheets_configured():
            log("ERROR: Google Sheets not configured")
            log("Set GOOGLE_SHEET_ID and GOOGLE_SHEETS_CREDENTIALS environment variables")
            return 1

    # Initialize sheets only mode
    if args.init_sheets:
        log("Initializing Google Sheets structure only...")
        try:
            from sheets_sync import SheetsSync
            sheets = SheetsSync()
            if sheets.connect():
                sheets.initialize_sheets()
                sheets.populate_districts()
                log("Google Sheets initialized successfully!")
                return 0
            else:
                log("Could not connect to Google Sheets")
                return 1
        except Exception as e:
            log(f"Error: {e}")
            return 1

    # Load state
    log("Loading state file...")
    state = load_state()
    if not state:
        log("No state data found")
        return 1

    # Get all candidates
    log("Extracting candidates from state...")
    candidates = get_all_candidates(state)
    log(f"Found {len(candidates)} unique candidates")

    if not candidates:
        log("No candidates to process")
        return 0

    # Load incumbents for party detection
    log("Loading incumbents data...")
    incumbents = load_incumbents()
    house_count = len(incumbents.get("house", {}))
    senate_count = len(incumbents.get("senate", {}))
    log(f"Loaded {house_count} House + {senate_count} Senate incumbents")

    # Detect parties
    party_results = {}
    if not args.skip_party_detection:
        log("Detecting party affiliations...")
        for i, c in enumerate(candidates):
            name = c["candidate_name"]
            log(f"  [{i+1}/{len(candidates)}] {name}")

            party_info = detect_party_for_candidate(c, incumbents)
            party_results[name] = party_info

            party = party_info.get("party", "?")
            confidence = party_info.get("confidence", "UNKNOWN")
            source = party_info.get("source", "none")
            log(f"    -> {party} ({confidence}) via {source}")

        # Summary
        parties_found = sum(1 for r in party_results.values() if r.get("party"))
        log(f"Party detection complete: {parties_found}/{len(candidates)} detected")
    else:
        log("Skipping party detection (--skip-party-detection)")

    # Backfill to Google Sheets
    log("Syncing to Google Sheets...")
    success = backfill_google_sheets(candidates, party_results, dry_run=args.dry_run)

    if success:
        log("=" * 60)
        log("Backfill completed successfully!")
        log("=" * 60)
        return 0
    else:
        log("=" * 60)
        log("Backfill failed - see errors above")
        log("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())

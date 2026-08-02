"""
Disaster Data Parser
Normalizes raw API responses from GDACS and USGS into a
unified DisasterZone-compatible format and saves to DB
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from typing import List, Dict, Any
from data_ingestion.connectors.gdacs_connector import gdacs
from data_ingestion.connectors.usgs_connector  import usgs


def parse_and_classify_all() -> Dict[str, Any]:
    """
    Fetch from GDACS + USGS, classify each event, return summary.
    Call this from the /api/feeds/classify endpoint.
    """
    from app.services.zone_classifier import classify_gdacs_event, classify_usgs_event

    results = {
        "gdacs_events":  [],
        "usgs_events":   [],
        "classified_zones": [],
        "errors": [],
    }

    # ── GDACS ────────────────────────────────────────────────────────────────
    try:
        gdacs_raw = gdacs.fetch_all_india()
        results["gdacs_events"] = gdacs_raw
        for event in gdacs_raw:
            zone = classify_gdacs_event(event)
            if zone:
                results["classified_zones"].append(zone)
    except Exception as e:
        results["errors"].append(f"GDACS fetch error: {e}")

    # ── USGS ─────────────────────────────────────────────────────────────────
    try:
        usgs_raw = usgs.fetch_recent()
        results["usgs_events"] = usgs_raw
        for feature in usgs_raw:
            zone = classify_usgs_event(feature)
            if zone:
                results["classified_zones"].append(zone)
    except Exception as e:
        results["errors"].append(f"USGS fetch error: {e}")

    print(f"[Parser] Total classified zones: {len(results['classified_zones'])}")
    return results


def get_live_feed_summary() -> Dict[str, Any]:
    """Quick summary of current live events (no DB save)."""
    gdacs_events = gdacs.fetch_all_india()
    usgs_events  = usgs.fetch_recent()
    usgs_summary = usgs.get_summary(usgs_events)

    return {
        "gdacs": {
            "count":  len(gdacs_events),
            "events": gdacs_events[:10],  # return top 10
        },
        "usgs": {
            "count":   usgs_summary["count"],
            "summary": usgs_summary,
            "events":  usgs_events[:10],
        },
        "total_events": len(gdacs_events) + usgs_summary["count"],
    }

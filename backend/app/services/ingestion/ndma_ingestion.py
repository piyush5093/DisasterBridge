"""
Normalizes parsed NDMA CAP alerts (app/utils/cap_parser.py) into
DisasterEvent rows, reusing the same `disaster_events` table as GDACS
and USGS (source="NDMA").

Field mapping notes:
- CAP's <event> is free text (e.g. "Flood", "Heavy Rainfall Warning",
  "Cyclone Alert") rather than an enum — mapped to GDACS-style 2-letter
  codes via a best-effort keyword match (_EVENT_TYPE_KEYWORDS below).
  Unmatched events fall back to "OT" (other) rather than guessing, and
  the original free-text `event` is always preserved in `raw_data`.
- CAP's <severity> (Extreme/Severe/Moderate/Minor/Unknown) is mapped to
  GDACS-style alert levels (Red/Orange/Green) for consistency with the
  other two sources' `alert_level` column — Extreme/Severe -> Red,
  Moderate -> Orange, Minor/Unknown -> Green.
- `episode_id` is always "0": CAP has no episode concept like GDACS: a
  msgType="Update" or "Cancel" for the same `identifier` is a distinct
  CAP message and would need its own row/history rather than being
  treated as an episode of the original — not implemented in this pass,
  noted for Day 5.
- geom is the centroid of the first polygon/circle found in the alert's
  area block. NDMA/CAP alerts are often issued per-district and may
  cover large multi-district areas — a single centroid point is a
  simplification consistent with how GDACS's own polygon events are
  already being centroid-reduced (see gdacs_ingestion.py).
- country is always "India" / iso3 "IND" since SACHET is India-only.
"""

from datetime import datetime, timezone
from typing import Any

from app.schemas.disaster_event import IngestionResult
from app.services.ingestion.common import upsert_normalized_events
from app.utils.cap_parser import ParsedCapAlert

SOURCE_NAME = "NDMA"

_EVENT_TYPE_KEYWORDS: dict[str, str] = {
    "flood": "FL",
    "flash flood": "FL",
    "cyclone": "TC",
    "storm": "TC",
    "earthquake": "EQ",
    "tsunami": "TS",
    "fire": "WF",
    "forest fire": "WF",
    "drought": "DR",
    "heat": "HW",  # heatwave — not in GDACS's set, kept distinct rather than forced into DR/WF
    "cold": "CW",  # coldwave, same rationale
    "landslide": "LS",
    "avalanche": "AV",
    "rainfall": "FL",  # heavy-rainfall warnings are flood-precursor alerts in NDMA's practice
    "thunderstorm": "TS_STORM",
}

_SEVERITY_TO_ALERT_LEVEL: dict[str, str] = {
    "extreme": "Red",
    "severe": "Red",
    "moderate": "Orange",
    "minor": "Green",
    "unknown": "Green",
}


def _map_event_type(cap_event: str | None) -> str:
    if not cap_event:
        return "OT"
    lowered = cap_event.lower()
    for keyword, code in _EVENT_TYPE_KEYWORDS.items():
        if keyword in lowered:
            return code
    return "OT"


def normalize_alert(alert: ParsedCapAlert) -> dict[str, Any] | None:
    """
    Convert a ParsedCapAlert into a flat dict matching DisasterEvent's
    columns. Returns None if the alert has no usable location (CAP
    technically allows an <info> block with no <area>, though NDMA
    alerts should always include one for a geo-targeted system).
    """
    if not alert.points:
        return None

    lon, lat = alert.points[0]  # first polygon/circle centroid

    severity_key = (alert.severity or "unknown").lower()

    return {
        "source": SOURCE_NAME,
        "external_event_id": alert.identifier,
        "episode_id": "0",
        "event_type": _map_event_type(alert.event),
        "event_name": alert.headline or alert.event,
        "glide_number": None,
        "alert_level": _SEVERITY_TO_ALERT_LEVEL.get(severity_key, "Green"),
        "alert_score": None,  # CAP has no numeric score; severity/urgency/certainty are categorical
        "severity_value": None,
        "severity_unit": None,
        "population_exposed": None,
        "country": "India",
        "iso3": "IND",
        "location": {"type": "Point", "coordinates": [lon, lat]},
        "from_date": alert.effective or alert.sent,
        "to_date": alert.expires,
        "is_current": alert.status == "Actual" and alert.msg_type != "Cancel",
        "source_url": None,
        "raw_data": alert.raw_properties,
    }


async def upsert_alert(alert: ParsedCapAlert) -> IngestionResult:
    """
    Normalize and upsert a single parsed CAP alert. Unlike GDACS/USGS's
    batch `upsert_events`, NDMA alerts are fetched one identifier at a
    time (see ndma_client.py's discovery limitation), so this takes one
    alert rather than a list.
    """
    normalized = normalize_alert(alert)
    if normalized is None:
        return IngestionResult(
            source=SOURCE_NAME,
            fetched=1,
            created=0,
            updated=0,
            skipped=1,
            errors=[f"Alert {alert.identifier} has no usable area/geometry — skipped"],
        )

    return await upsert_normalized_events(SOURCE_NAME, [normalized], total_fetched=1)

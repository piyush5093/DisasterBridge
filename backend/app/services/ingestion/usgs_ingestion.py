"""
Normalizes USGS earthquake GeoJSON features into DisasterEvent rows.

Reuses the same `disaster_events` table as GDACS (source="USGS") so
downstream modules (geospatial impact, demand prediction) query one
schema regardless of feed. Some fields don't map cleanly between USGS
and GDACS conventions — documented per-field below rather than silently
guessing:

- USGS has no concept of "episodes" (each earthquake is one immutable
  catalog entry, occasionally revised in place as more data comes in).
  `episode_id` is always "0"; re-ingesting the same `id` updates the row
  in place via the existing (source, external_event_id, episode_id)
  unique constraint — which is exactly the right behavior for a
  magnitude/location revision.
- USGS's `alert` field (PAGER impact alert: green/yellow/orange/red) is
  a DIFFERENT scale from GDACS's 3-level alert (Green/Orange/Red) and is
  only present for larger events. Stored as-is (capitalized) rather than
  remapped, since collapsing yellow into orange or red would lose signal.
- `sig` ("significance", USGS's own 0-1000+ severity score) is stored in
  `alert_score` as the closest analogous field GDACS's schema offers.
- USGS gives no country/ISO3 — only a free-text `place` description
  (e.g. "20 km ESE of Farkhār, Afghanistan"). Left as None rather than
  guessing from string-parsing `place`, which is unreliable across
  locales/oceanic events ("165km SSW of ...", offshore regions, etc.).
  `place` itself is preserved in `event_name` and `raw_data`.
- `is_current` is always True: USGS events don't have a GDACS-style
  "still ongoing hazard" concept — they're point-in-time catalog facts,
  "current" here just means "present in the catalog".

This mirrors gdacs_ingestion.py's structure closely, and Day 5's planned
"data normalization pipeline" is where these two (soon three, once NDMA
also writes into `disaster_events`) per-source normalizers get collapsed
into one shared upsert path — kept separate for now so Day 2's
already-tested GDACS path isn't touched while USGS is being built.
"""

from datetime import datetime, timezone
from typing import Any

from app.schemas.disaster_event import IngestionResult
from app.services.ingestion.common import upsert_normalized_events

SOURCE_NAME = "USGS"


def _epoch_ms_to_datetime(value: Any) -> datetime | None:
    """USGS times are Unix epoch milliseconds (confirmed live), UTC."""
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None


def normalize_feature(feature: dict[str, Any]) -> dict[str, Any] | None:
    """
    Convert one GeoJSON feature from a USGS response into a flat dict
    matching DisasterEvent's columns. Returns None if the feature is
    missing the minimum required fields (id/geometry).
    """
    event_id = feature.get("id")
    props = feature.get("properties", {}) or {}
    geometry = feature.get("geometry")

    if not event_id or not geometry or geometry.get("type") != "Point":
        return None

    coords = geometry.get("coordinates") or []
    if len(coords) < 2:
        return None
    lon, lat = coords[0], coords[1]
    depth_km = coords[2] if len(coords) > 2 else None

    mag = props.get("mag")
    mag_type = props.get("magType") or "M"
    severity_text = None
    if mag is not None:
        severity_text = f"Magnitude {mag}{mag_type.upper()}" + (
            f", Depth:{depth_km:.1f}km" if depth_km is not None else ""
        )

    alert = props.get("alert")  # "green" | "yellow" | "orange" | "red" | None

    return {
        "source": SOURCE_NAME,
        "external_event_id": str(event_id),
        "episode_id": "0",
        "event_type": "EQ" if props.get("type") == "earthquake" else str(props.get("type", "EQ")).upper()[:10],
        "event_name": props.get("title") or props.get("place"),
        "glide_number": None,
        "alert_level": alert.capitalize() if alert else None,
        "alert_score": props.get("sig"),
        "severity_value": mag,
        "severity_unit": mag_type.upper() if mag is not None else None,
        "population_exposed": None,  # would require the PAGER product, not in the base feed
        "country": None,  # no structured country field in USGS's response — see module docstring
        "iso3": None,
        "location": {"type": "Point", "coordinates": [lon, lat]},
        "from_date": _epoch_ms_to_datetime(props.get("time")),
        "to_date": _epoch_ms_to_datetime(props.get("time")),  # instantaneous event, same as from_date
        "is_current": True,
        "source_url": props.get("url") or props.get("detail"),
        "raw_data": {**props, "depth_km": depth_km, "severitytext": severity_text},
    }


async def upsert_events(features: list[dict[str, Any]]) -> IngestionResult:
    """
    Normalize and upsert a list of USGS GeoJSON features. Same idempotent
    upsert-by-natural-key behavior as gdacs_ingestion.upsert_events.
    """
    normalized_list = []
    skipped = 0
    errors: list[str] = []

    for feature in features:
        normalized = normalize_feature(feature)
        if normalized is None:
            skipped += 1
            errors.append(f"Skipped feature missing required fields: {feature.get('id', '<unknown>')}")
            continue
        normalized_list.append(normalized)

    return await upsert_normalized_events(
        SOURCE_NAME, normalized_list, total_fetched=len(features), skipped=skipped, errors=errors
    )

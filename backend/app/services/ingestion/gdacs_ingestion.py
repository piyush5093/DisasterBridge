"""
Normalizes GDACS GeoJSON features into DisasterEvent rows and upserts them.

Field mapping is defensive by design: every property is read with
`.get()` and multiple candidate key names where GDACS documentation was
ambiguous, because this was built without a live sample response to
confirm exact key names (see gdacs_client.py docstring). The full,
untouched properties dict is always stored in `raw_data`, so:
  - nothing is lost if a mapped field is actually named differently
  - you can re-run `renormalize_from_raw()` (bottom of this file) later
    against stored raw_data without hitting the API again, once you've
    confirmed real field names from a live response.

Upsert key: (source, external_event_id, episode_id) — matches the
DisasterEvent unique constraint. GDACS re-issues an event as it evolves
(e.g. a cyclone's forecast track shifts); each episode is kept as its
own row rather than overwritten, so history is preserved for later
demand-recalibration logic (Week 3).
"""

from datetime import datetime, timezone
from typing import Any

from shapely.geometry import shape

from app.schemas.disaster_event import IngestionResult
from app.services.ingestion.common import upsert_normalized_events

SOURCE_NAME = "GDACS"


def _first_of(props: dict[str, Any], *keys: str) -> Any:
    """Return the first present, non-None value among candidate keys."""
    for key in keys:
        if key in props and props[key] is not None:
            return props[key]
    return None


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        # Confirmed against a live GDACS response (2026-07-24): dates come
        # back as naive ISO-8601 with no 'Z'/offset (e.g. "2026-07-23T06:00:00"),
        # not the "...Z" form originally assumed. Handle both: strip/convert
        # 'Z' if present, then assume UTC if still naive, since GDACS times
        # are UTC and our `from_date`/`to_date` columns are timezone-aware.
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def normalize_feature(feature: dict[str, Any]) -> dict[str, Any] | None:
    """
    Convert one GeoJSON feature from a GDACS response into a flat dict
    matching DisasterEvent's columns. Returns None if the feature is
    missing the minimum required fields (event id/type/geometry).
    """
    props = feature.get("properties", {}) or {}
    geometry = feature.get("geometry")

    event_id = _first_of(props, "eventid", "eventId")
    event_type = _first_of(props, "eventtype", "eventType")
    episode_id = str(_first_of(props, "episodeid", "episodeId") or "0")

    if event_id is None or event_type is None or geometry is None:
        return None

    severity = _first_of(props, "severitydata", "severityData") or {}
    if not isinstance(severity, dict):
        severity = {}

    population = _first_of(props, "population", "populationdata", "populationData")
    population_value = None
    if isinstance(population, dict):
        population_value = _first_of(population, "value", "population")
    elif isinstance(population, (int, float)):
        population_value = population

    url_block = _first_of(props, "url") or {}
    if not isinstance(url_block, dict):
        url_block = {}

    try:
        geom_shape = shape(geometry)
        # GDACS sometimes returns polygons/lines for large-footprint events
        # (e.g. flood extent); reduce to a representative point so every
        # row has a consistent POINT geometry for map/zone logic.
        point = geom_shape.centroid if geom_shape.geom_type != "Point" else geom_shape
    except Exception:
        return None

    return {
        "source": SOURCE_NAME,
        "external_event_id": str(event_id),
        "episode_id": episode_id,
        "event_type": str(event_type),
        "event_name": _first_of(props, "eventname", "name", "title"),
        "glide_number": _first_of(props, "glide"),
        "alert_level": _first_of(props, "alertlevel", "episodealertlevel"),
        "alert_score": _first_of(props, "alertscore", "episodealertscore"),
        "severity_value": _first_of(severity, "severity", "value"),
        "severity_unit": _first_of(severity, "severityunit", "unit"),
        "population_exposed": population_value,
        "country": _first_of(props, "country"),
        "iso3": _first_of(props, "iso3"),
        "location": {"type": "Point", "coordinates": [point.x, point.y]},
        "from_date": _parse_datetime(_first_of(props, "fromdate")),
        "to_date": _parse_datetime(_first_of(props, "todate")),
        "is_current": _first_of(props, "iscurrent") in (True, "true", "True", None),
        "source_url": _first_of(url_block, "report", "details", "geometry"),
        "raw_data": props,
    }


async def upsert_events(features: list[dict[str, Any]]) -> IngestionResult:
    """
    Normalize and upsert a list of GeoJSON features. Safe to call
    repeatedly — existing (source, external_event_id, episode_id)
    documents are updated in place rather than duplicated.
    """
    normalized_list = []
    skipped = 0
    errors: list[str] = []

    for feature in features:
        normalized = normalize_feature(feature)
        if normalized is None:
            skipped += 1
            errors.append(
                f"Skipped feature missing required fields: "
                f"{feature.get('properties', {}).get('eventid', '<unknown>')}"
            )
            continue
        normalized_list.append(normalized)

    return await upsert_normalized_events(
        SOURCE_NAME, normalized_list, total_fetched=len(features), skipped=skipped, errors=errors
    )

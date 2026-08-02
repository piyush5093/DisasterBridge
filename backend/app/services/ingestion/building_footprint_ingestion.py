"""
Normalizes Overpass API elements into BuildingFootprint documents.

Ways become GeoJSON Polygons (closing the ring if Overpass's geometry
array isn't already closed — most building ways are closed loops, but
this isn't guaranteed for every OSM edit). Standalone building=* nodes
become GeoJSON Points.

MongoDB's 2dsphere index requires valid GeoJSON (no self-intersections,
correct ring winding isn't required but degenerate rings are rejected).
Real-world OSM data occasionally has invalid geometries (e.g. a way with
only 2 distinct points) — these are skipped rather than left to crash
the whole batch on insert, consistent with how malformed GDACS/USGS
features are handled (Days 2-3).
"""

from typing import Any

from pymongo.errors import WriteError

from app.models.building_footprint import BuildingFootprint


def _way_to_polygon(element: dict[str, Any]) -> dict[str, Any] | None:
    geometry = element.get("geometry")
    if not geometry or len(geometry) < 3:
        return None  # not enough points for a polygon

    ring = [[point["lon"], point["lat"]] for point in geometry]
    if ring[0] != ring[-1]:
        ring.append(ring[0])  # close the ring if Overpass didn't

    return {"type": "Polygon", "coordinates": [ring]}


def _node_to_point(element: dict[str, Any]) -> dict[str, Any] | None:
    lon, lat = element.get("lon"), element.get("lat")
    if lon is None or lat is None:
        return None
    return {"type": "Point", "coordinates": [lon, lat]}


def normalize_element(element: dict[str, Any]) -> dict[str, Any] | None:
    """Convert one Overpass element into a flat dict matching BuildingFootprint's fields."""
    osm_type = element.get("type")
    osm_id = element.get("id")
    if osm_type not in ("way", "node") or osm_id is None:
        return None

    geometry = _way_to_polygon(element) if osm_type == "way" else _node_to_point(element)
    if geometry is None:
        return None

    tags = element.get("tags", {}) or {}

    return {
        "osm_id": osm_id,
        "osm_type": osm_type,
        "building_type": tags.get("building"),
        "geometry": geometry,
        "tags": tags,
    }


async def upsert_footprints(elements: list[dict[str, Any]]) -> dict[str, int]:
    """Normalize and upsert Overpass elements, keyed on (osm_type, osm_id)."""
    fetched = len(elements)
    created = updated = skipped = invalid_geometry = 0

    for element in elements:
        normalized = normalize_element(element)
        if normalized is None:
            skipped += 1
            continue

        existing = await BuildingFootprint.find_one(
            BuildingFootprint.osm_type == normalized["osm_type"],
            BuildingFootprint.osm_id == normalized["osm_id"],
        )

        try:
            if existing:
                for key, value in normalized.items():
                    setattr(existing, key, value)
                await existing.save()
                updated += 1
            else:
                await BuildingFootprint(**normalized).insert()
                created += 1
        except WriteError:
            # Invalid GeoJSON per MongoDB's 2dsphere validation (e.g. a
            # self-intersecting polygon from messy OSM source data) —
            # skip this one building rather than aborting the batch.
            invalid_geometry += 1

    return {
        "fetched": fetched,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "invalid_geometry": invalid_geometry,
    }

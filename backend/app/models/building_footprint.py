"""
Building footprint storage — one document per OSM way/node tagged
building=*. Used by Day 10's grid-cell severity scoring (building
density per cell is one of the inputs) and can back frontend map
layers directly (each document's `geometry` is already GeoJSON).
"""

from datetime import datetime, timezone
from typing import Any

from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, GEOSPHERE, IndexModel


class BuildingFootprint(Document):
    osm_id: int
    osm_type: str  # "way" | "node"
    building_type: str | None = None  # value of the `building` tag, e.g. "yes", "residential", "hospital"
    geometry: dict[str, Any]  # GeoJSON Polygon (from ways) or Point (from standalone nodes)
    tags: dict[str, Any] = Field(default_factory=dict)

    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "building_footprints"
        indexes = [
            IndexModel([("osm_type", ASCENDING), ("osm_id", ASCENDING)], unique=True, name="uq_osm_type_id"),
            IndexModel([("geometry", GEOSPHERE)], name="geo_2dsphere"),
        ]

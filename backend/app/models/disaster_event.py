"""
Normalized disaster event storage (MongoDB, via Beanie).

Deliberately source-agnostic: GDACS, USGS, and NDMA all write into this
same collection with a `source` discriminator, rather than one collection
per feed. That keeps every downstream module (geospatial impact
assessment, demand prediction, etc.) working against a single schema
regardless of source.

Location is stored as a GeoJSON Point (`{"type": "Point", "coordinates":
[lon, lat]}`) with a 2dsphere index, so `$near`/`$geoWithin`/`$geoIntersects`
queries work directly — the Mongo equivalent of PostGIS's ST_DWithin/
ST_Contains once zones exist (Day 10). Note this covers point-based
geospatial queries but NOT raster data (population density grids, Day 7)
the way PostGIS's raster extension would — raster storage will need a
different approach (e.g. files on disk/object storage + metadata in
Mongo) when Day 7 is built.
"""

from datetime import datetime, timezone
from typing import Literal

from beanie import Document
from pydantic import BaseModel, Field
from pymongo import ASCENDING, GEOSPHERE, IndexModel


class GeoPoint(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: list[float]  # [longitude, latitude] — GeoJSON order


class DisasterEvent(Document):
    """
    One document = one (source, external_event_id, episode_id) observation
    of a disaster event. Episodes matter because GDACS re-issues an event
    as it evolves (e.g. a cyclone's path updates); each episode is kept as
    its own document rather than overwritten, so history is preserved.
    """

    # --- Provenance ---
    source: str  # GDACS | USGS | NDMA
    external_event_id: str
    episode_id: str = "0"

    # --- Classification ---
    event_type: str  # EQ, FL, TC, VO, WF, DR, ...
    event_name: str | None = None
    glide_number: str | None = None

    # --- Severity / alerting (GDACS-style; None for sources that don't provide it) ---
    alert_level: str | None = None  # Green/Orange/Red
    alert_score: float | None = None
    severity_value: float | None = None
    severity_unit: str | None = None
    population_exposed: int | None = None

    # --- Location ---
    country: str | None = None
    iso3: str | None = None
    location: GeoPoint | None = None
    impact_extent: dict | None = None  # GeoJSON Polygon, computed by app/services/impact (Day 6)

    # --- Timing ---
    from_date: datetime | None = None
    to_date: datetime | None = None
    is_current: bool = True

    # --- Traceability ---
    source_url: str | None = None
    raw_data: dict = Field(default_factory=dict)

    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "disaster_events"
        indexes = [
            IndexModel(
                [("source", ASCENDING), ("external_event_id", ASCENDING), ("episode_id", ASCENDING)],
                unique=True,
                name="uq_source_external_episode",
            ),
            IndexModel([("location", GEOSPHERE)], name="geo_2dsphere"),
            IndexModel([("event_type", ASCENDING)], name="idx_event_type"),
            IndexModel([("alert_level", ASCENDING)], name="idx_alert_level"),
            IndexModel([("is_current", ASCENDING)], name="idx_is_current"),
            IndexModel([("country", ASCENDING)], name="idx_country"),
        ]

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<DisasterEvent {self.source}:{self.event_type}:"
            f"{self.external_event_id} ep={self.episode_id}>"
        )

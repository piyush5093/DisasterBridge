"""
Pydantic schemas for the disaster_events resource.

DisasterEventOut mirrors the DisasterEvent Beanie document for API
responses (flattening `location` into longitude/latitude for easier
client consumption, same as the previous PostGIS-backed version did).
IngestionResult summarizes what an ingestion run did — used by the
/ingest/* endpoints so the caller can see counts without querying the
DB separately.
"""

from datetime import datetime

from pydantic import BaseModel


class DisasterEventOut(BaseModel):
    id: str
    source: str
    external_event_id: str
    episode_id: str
    event_type: str
    event_name: str | None
    glide_number: str | None
    alert_level: str | None
    alert_score: float | None
    severity_value: float | None
    severity_unit: str | None
    population_exposed: int | None
    country: str | None
    iso3: str | None
    longitude: float | None
    latitude: float | None
    from_date: datetime | None
    to_date: datetime | None
    is_current: bool
    source_url: str | None
    ingested_at: datetime
    updated_at: datetime


class IngestionResult(BaseModel):
    source: str
    fetched: int
    created: int
    updated: int
    skipped: int
    errors: list[str] = []

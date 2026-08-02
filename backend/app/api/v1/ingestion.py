"""
GDACS ingestion + disaster event listing endpoints.

POST /ingest/gdacs/active   -> pulls EVENTS4APP (everything currently active)
POST /ingest/gdacs/search   -> pulls SEARCH with filters (date range, types, alert level)
GET  /events                -> lists stored events (any source), with filters

These are synchronous-to-call for Day 2 (call them directly / from a
script or cron). Day 5's ingestion pipeline wraps the same `upsert_events`
service in a Celery task for scheduled polling — the normalization logic
here doesn't change, only how it's triggered.
"""

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.models.disaster_event import DisasterEvent
from app.schemas.disaster_event import DisasterEventOut, IngestionResult
from app.services.external.gdacs_client import GDACSClient, GDACSClientError
from app.services.ingestion.gdacs_ingestion import upsert_events

router = APIRouter(prefix="/ingest/gdacs", tags=["ingestion"])
events_router = APIRouter(tags=["events"])


def _event_to_out(event: DisasterEvent) -> DisasterEventOut:
    return DisasterEventOut(
        id=str(event.id),
        source=event.source,
        external_event_id=event.external_event_id,
        episode_id=event.episode_id,
        event_type=event.event_type,
        event_name=event.event_name,
        glide_number=event.glide_number,
        alert_level=event.alert_level,
        alert_score=event.alert_score,
        severity_value=event.severity_value,
        severity_unit=event.severity_unit,
        population_exposed=event.population_exposed,
        country=event.country,
        iso3=event.iso3,
        longitude=event.location.coordinates[0] if event.location else None,
        latitude=event.location.coordinates[1] if event.location else None,
        from_date=event.from_date,
        to_date=event.to_date,
        is_current=event.is_current,
        source_url=event.source_url,
        ingested_at=event.ingested_at,
        updated_at=event.updated_at,
    )


@router.post("/active", response_model=IngestionResult)
async def ingest_active_events() -> IngestionResult:
    """Pull all currently active events from GDACS (EVENTS4APP) and upsert them."""
    client = GDACSClient()
    try:
        geojson = await client.get_active_events()
    except GDACSClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    features = geojson.get("features", [])
    return await upsert_events(features)


@router.post("/search", response_model=IngestionResult)
async def ingest_search_events(
    event_types: str | None = Query(
        None, description="Semicolon-separated GDACS codes, e.g. 'EQ;TC;FL'"
    ),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    alert_level: str | None = Query(None, description="green | orange | red"),
) -> IngestionResult:
    """Custom-filtered pull from GDACS's SEARCH endpoint, then upsert."""
    client = GDACSClient()
    types_list = event_types.split(";") if event_types else None
    try:
        geojson = await client.search_events(
            event_types=types_list,
            from_date=from_date,
            to_date=to_date,
            alert_level=alert_level,
        )
    except GDACSClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    features = geojson.get("features", [])
    return await upsert_events(features)


@events_router.get("/events", response_model=list[DisasterEventOut])
async def list_events(
    source: str | None = Query(None),
    event_type: str | None = Query(None),
    alert_level: str | None = Query(None),
    country: str | None = Query(None),
    is_current: bool | None = Query(None),
    limit: int = Query(100, le=500),
) -> list[DisasterEventOut]:
    """List normalized disaster events currently stored in the DB."""
    query_conditions = []
    if source:
        query_conditions.append(DisasterEvent.source == source.upper())
    if event_type:
        query_conditions.append(DisasterEvent.event_type == event_type.upper())
    if alert_level:
        query_conditions.append(DisasterEvent.alert_level == alert_level.capitalize())
    if country:
        query_conditions.append(DisasterEvent.country == country)
    if is_current is not None:
        query_conditions.append(DisasterEvent.is_current == is_current)

    events = (
        await DisasterEvent.find(*query_conditions)
        .sort(-DisasterEvent.from_date)
        .limit(limit)
        .to_list()
    )
    return [_event_to_out(e) for e in events]

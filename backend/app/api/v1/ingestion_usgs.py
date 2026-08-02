"""
USGS earthquake ingestion endpoints.

POST /ingest/usgs/query      -> custom FDSN query (magnitude/date/bbox filters)
POST /ingest/usgs/summary    -> pull a pre-computed real-time summary feed

Stored events land in the same `disaster_events` table as GDACS
(source="USGS"); use GET /api/v1/events?source=USGS to list them.
"""

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.schemas.disaster_event import IngestionResult
from app.services.external.usgs_client import USGSClient, USGSClientError
from app.services.ingestion.usgs_ingestion import upsert_events

router = APIRouter(prefix="/ingest/usgs", tags=["ingestion"])


@router.post("/query", response_model=IngestionResult)
async def ingest_usgs_query(
    start_time: date | None = Query(None),
    end_time: date | None = Query(None),
    min_magnitude: float | None = Query(4.5, description="Minimum magnitude (defaults to 4.5 to keep pulls small)"),
    min_latitude: float | None = Query(None),
    max_latitude: float | None = Query(None),
    min_longitude: float | None = Query(None),
    max_longitude: float | None = Query(None),
) -> IngestionResult:
    """Custom-filtered pull from USGS's FDSN query endpoint, then upsert."""
    client = USGSClient()
    try:
        geojson = await client.query_earthquakes(
            start_time=start_time,
            end_time=end_time,
            min_magnitude=min_magnitude,
            min_latitude=min_latitude,
            max_latitude=max_latitude,
            min_longitude=min_longitude,
            max_longitude=max_longitude,
        )
    except USGSClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    features = geojson.get("features", [])
    return await upsert_events(features)


@router.post("/summary", response_model=IngestionResult)
async def ingest_usgs_summary(
    feed: str = Query(
        "significant_week",
        description="One of significant|4.5|2.5|1.0|all combined with _hour|_day|_week|_month, e.g. '4.5_day'",
    ),
) -> IngestionResult:
    """Pull a pre-computed real-time summary feed and upsert it."""
    client = USGSClient()
    try:
        geojson = await client.get_summary_feed(feed=feed)
    except USGSClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    features = geojson.get("features", [])
    return await upsert_events(features)

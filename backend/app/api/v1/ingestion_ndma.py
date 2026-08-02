"""
NDMA CAP alert ingestion endpoint.

POST /ingest/ndma/alert?identifier=<CAP_IDENTIFIER> -> fetch one alert by
its CAP identifier and upsert it.

See ndma_client.py's module docstring for the current limitation: there
is no confirmed public endpoint to discover *which* identifiers are
currently active, so this only supports fetching a specific, already-known
identifier (e.g. supplied manually, or from a partner system) rather than
"pull everything active" like GDACS/USGS's endpoints do.

A single NDMAClient is kept at module scope so its ETag cache persists
across requests within this process, per NDMA's mandatory-caching
integration guide.
"""

from fastapi import APIRouter, HTTPException, Query

from app.schemas.disaster_event import IngestionResult
from app.services.external.ndma_client import NDMAClient, NDMAClientError
from app.services.ingestion.ndma_ingestion import upsert_alert

router = APIRouter(prefix="/ingest/ndma", tags=["ingestion"])

_ndma_client = NDMAClient()


@router.post("/alert", response_model=IngestionResult)
async def ingest_ndma_alert(
    identifier: str = Query(..., description="CAP alert identifier from NDMA's SACHET feed"),
) -> IngestionResult:
    try:
        alert = await _ndma_client.fetch_alert(identifier)
    except NDMAClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if alert is None:
        # 304 Not Modified — nothing changed since the last fetch.
        return IngestionResult(source="NDMA", fetched=0, created=0, updated=0, skipped=0)

    return await upsert_alert(alert)

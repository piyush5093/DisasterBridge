"""
On-demand pipeline trigger — runs the same GDACS+USGS ingestion the
Celery beat schedule runs periodically (see app/core/celery_app.py),
callable synchronously via the API for manual runs/testing without
needing Celery/Redis set up locally.
"""

from fastapi import APIRouter

from app.services.ingestion.pipeline import run_full_ingestion

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/run-all")
async def run_all_ingestion() -> dict:
    run = await run_full_ingestion()
    return {
        "created": run.total_created,
        "updated": run.total_updated,
        "skipped": run.total_skipped,
        "per_source": [r.model_dump() for r in run.results],
        "failures": run.failures,
    }

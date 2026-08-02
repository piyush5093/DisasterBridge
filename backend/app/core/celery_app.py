"""
Celery app for scheduled/async jobs — currently just periodic ingestion
(this is the "Redis + Celery (optional)" piece from the stack: async
recalibration/ingestion jobs).

Run a worker locally with:
    celery -A app.core.celery_app worker --loglevel=info
Run the beat scheduler (for the periodic pull below) with:
    celery -A app.core.celery_app beat --loglevel=info

Note: Celery's default task functions are sync; `run_full_ingestion` is
async (it awaits Motor/Beanie calls), so the task wraps it in
`asyncio.run(...)`. This is fine for a periodic job running in its own
worker process — just don't call `run_full_ingestion_task` from inside
an already-running event loop (e.g. from within a FastAPI request).
"""

import asyncio

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "disaster_response",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.beat_schedule = {
    "poll-gdacs-usgs-every-15-minutes": {
        "task": "app.core.celery_app.run_full_ingestion_task",
        "schedule": crontab(minute="*/15"),
    },
}
celery_app.conf.timezone = "UTC"


@celery_app.task(name="app.core.celery_app.run_full_ingestion_task")
def run_full_ingestion_task() -> dict:
    """
    Celery entrypoint for the periodic GDACS+USGS pull. Each task
    invocation needs its own Mongo connection since it runs in a
    separate worker process from the FastAPI app — connect, run, and
    disconnect within the task rather than relying on app.main's
    lifespan (which only covers the API process).
    """

    async def _run() -> dict:
        from app.db.mongodb import close_mongo_connection, connect_to_mongo
        from app.services.ingestion.pipeline import run_full_ingestion

        await connect_to_mongo()
        try:
            run = await run_full_ingestion()
            return {
                "created": run.total_created,
                "updated": run.total_updated,
                "skipped": run.total_skipped,
                "failures": run.failures,
            }
        finally:
            await close_mongo_connection()

    return asyncio.run(_run())

"""
Health-check endpoints.

Day 1 goal: prove that (a) FastAPI is serving requests and (b) the app
can reach MongoDB before any real documents/collections exist.
"""

from fastapi import APIRouter

from app.db.mongodb import get_client

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    """Basic liveness probe — no DB dependency."""
    return {"status": "ok"}


@router.get("/health/db")
async def health_check_db() -> dict:
    """
    Liveness probe that also confirms MongoDB is reachable and reports
    its version. Fails loudly (500, via the RuntimeError in get_client()
    or a connection error from the `ping` command) if the DB is
    unreachable.
    """
    client = get_client()
    await client.admin.command("ping")
    build_info = await client.admin.command("buildInfo")

    return {
        "status": "ok",
        "mongodb_version": build_info.get("version"),
    }

"""
MongoDB connection lifecycle, using Motor (async driver) + Beanie (ODM).

Unlike the SQLAlchemy setup this replaces, there's no per-request session
dependency needed: `connect_to_mongo()` runs once at app startup (see
app/main.py's `lifespan`), calls `init_beanie(...)`, and after that every
Document subclass (e.g. DisasterEvent) can query/save directly —
`DisasterEvent.find(...)`, `doc.save()`, etc. — from anywhere, the same
way Beanie models work once initialized.

`get_client()` is exposed separately (rather than only living inside
connect_to_mongo) so health.py can run an independent `ping` command
without going through a Document model.
"""

from motor.motor_asyncio import AsyncIOMotorClient

from beanie import init_beanie

from app.core.config import settings
from app.models.building_footprint import BuildingFootprint
from app.models.disaster_event import DisasterEvent
from app.models.grid_cell import GridCell
from app.models.resource_inventory import ResourceInventory

_client: AsyncIOMotorClient | None = None


async def connect_to_mongo() -> None:
    global _client
    _client = AsyncIOMotorClient(settings.MONGODB_URL)
    await init_beanie(
        database=_client[settings.MONGODB_DB_NAME],
        document_models=[DisasterEvent, BuildingFootprint, ResourceInventory, GridCell],
    )


async def close_mongo_connection() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_client() -> AsyncIOMotorClient:
    if _client is None:
        raise RuntimeError(
            "MongoDB client not initialized — connect_to_mongo() must run "
            "at app startup before this is called (see app/main.py's lifespan)."
        )
    return _client

"""
Population-in-polygon endpoints, and a convenience version that pulls
the polygon straight from a stored event's `impact_extent` (Day 6) so
the two features compose: compute extent -> estimate exposed population
in one call chain.
"""

from beanie import PydanticObjectId
from fastapi import APIRouter, Body, HTTPException

from app.core.config import settings
from app.models.disaster_event import DisasterEvent
from app.services.population.density_service import PopulationRasterError, estimate_population_in_polygon

router = APIRouter(prefix="/population", tags=["population"])


@router.post("/estimate")
async def estimate_population(polygon: dict = Body(..., description="GeoJSON Polygon")) -> dict:
    try:
        return estimate_population_in_polygon(settings.POPULATION_RASTER_PATH, polygon)
    except PopulationRasterError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/estimate-for-event/{event_id}")
async def estimate_population_for_event(event_id: PydanticObjectId) -> dict:
    """
    Estimate population exposed within a stored event's impact extent
    (computed via POST /impact/{event_id}/compute in Day 6), and persist
    the result back onto the event's `population_exposed` field.
    """
    event = await DisasterEvent.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.impact_extent is None:
        raise HTTPException(
            status_code=422,
            detail="Event has no impact_extent yet — call POST /impact/{event_id}/compute first",
        )

    try:
        result = estimate_population_in_polygon(settings.POPULATION_RASTER_PATH, event.impact_extent)
    except PopulationRasterError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    event.population_exposed = result["estimated_population"]
    await event.save()

    return {"event_id": str(event.id), **result}

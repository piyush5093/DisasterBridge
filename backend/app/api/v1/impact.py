"""
Geospatial impact endpoints — compute and serve estimated impact-extent
polygons for events (see app/services/impact/extent_calculator.py for
the honesty caveats on how these are estimated).
"""

from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException

from app.models.disaster_event import DisasterEvent
from app.services.impact.extent_calculator import bbox_from_polygon, compute_impact_extent

router = APIRouter(prefix="/impact", tags=["impact"])


@router.post("/{event_id}/compute")
async def compute_event_impact_extent(event_id: PydanticObjectId) -> dict:
    """Compute (or recompute) the impact extent for one event and persist it."""
    event = await DisasterEvent.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.location is None:
        raise HTTPException(status_code=422, detail="Event has no location to compute an extent from")

    lon, lat = event.location.coordinates
    extent = compute_impact_extent(event.event_type, lon, lat, event.severity_value, event.alert_level)
    event.impact_extent = extent
    await event.save()

    return {"event_id": str(event.id), "impact_extent": extent, "bbox": bbox_from_polygon(extent)}


@router.post("/compute-all")
async def compute_all_missing_extents(only_current: bool = True) -> dict:
    """Batch-compute impact extents for every event that doesn't have one yet."""
    query = [DisasterEvent.impact_extent == None]  # noqa: E711 — Beanie comparison operator, not `is None`
    if only_current:
        query.append(DisasterEvent.is_current == True)  # noqa: E712

    events = await DisasterEvent.find(*query).to_list()

    computed = 0
    skipped_no_location = 0
    for event in events:
        if event.location is None:
            skipped_no_location += 1
            continue
        lon, lat = event.location.coordinates
        event.impact_extent = compute_impact_extent(
            event.event_type, lon, lat, event.severity_value, event.alert_level
        )
        await event.save()
        computed += 1

    return {"computed": computed, "skipped_no_location": skipped_no_location, "total_candidates": len(events)}


@router.get("/geojson")
async def impact_extents_as_geojson(only_current: bool = True) -> dict:
    """
    All computed impact extents as a GeoJSON FeatureCollection, ready to
    drop straight into a Leaflet layer on the frontend dashboard
    (Week 5-6) for flood/earthquake extent map rendering.
    """
    query = [DisasterEvent.impact_extent != None]  # noqa: E711
    if only_current:
        query.append(DisasterEvent.is_current == True)  # noqa: E712

    events = await DisasterEvent.find(*query).to_list()

    features = [
        {
            "type": "Feature",
            "geometry": event.impact_extent,
            "properties": {
                "event_id": str(event.id),
                "source": event.source,
                "event_type": event.event_type,
                "event_name": event.event_name,
                "alert_level": event.alert_level,
            },
        }
        for event in events
    ]

    return {"type": "FeatureCollection", "features": features}

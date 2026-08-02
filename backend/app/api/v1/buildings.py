"""
Building footprint endpoints — pull from OSM/Overpass and either
persist (for Day 10's grid-density scoring) or return live as GeoJSON.
"""

from fastapi import APIRouter, HTTPException, Query

from app.models.building_footprint import BuildingFootprint
from app.services.external.overpass_client import OverpassClient, OverpassClientError
from app.services.ingestion.building_footprint_ingestion import upsert_footprints

router = APIRouter(prefix="/buildings", tags=["buildings"])


@router.post("/ingest")
async def ingest_building_footprints(
    min_lon: float = Query(...),
    min_lat: float = Query(...),
    max_lon: float = Query(...),
    max_lat: float = Query(...),
) -> dict:
    """
    Pull building footprints for a bbox from Overpass and persist them.
    Keep bboxes reasonably small (city-district scale) — Overpass's
    public instance rate-limits/times-out large area queries.
    """
    client = OverpassClient()
    try:
        data = await client.get_building_footprints(min_lon, min_lat, max_lon, max_lat)
    except OverpassClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return await upsert_footprints(data.get("elements", []))


@router.get("/geojson")
async def building_footprints_geojson(
    min_lon: float = Query(...),
    min_lat: float = Query(...),
    max_lon: float = Query(...),
    max_lat: float = Query(...),
    limit: int = Query(5000, le=20000),
) -> dict:
    """Stored building footprints within a bbox, as a GeoJSON FeatureCollection."""
    docs = (
        await BuildingFootprint.find(
            {
                "geometry": {
                    "$geoWithin": {
                        "$box": [[min_lon, min_lat], [max_lon, max_lat]],
                    }
                }
            }
        )
        .limit(limit)
        .to_list()
    )

    features = [
        {
            "type": "Feature",
            "geometry": doc.geometry,
            "properties": {"osm_id": doc.osm_id, "osm_type": doc.osm_type, "building_type": doc.building_type},
        }
        for doc in docs
    ]

    return {"type": "FeatureCollection", "features": features}

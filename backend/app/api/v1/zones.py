"""
Grid-cell zone endpoints — Milestone 1: generate a severity-scored grid
over a region and serve it (as records or as a GeoJSON choropleth-ready
FeatureCollection for the frontend dashboard).
"""

from fastapi import APIRouter, HTTPException, Query

from app.models.grid_cell import GridCell
from app.services.zones.grid_classifier import generate_and_score_grid

router = APIRouter(prefix="/zones", tags=["zones"])


@router.post("/generate")
async def generate_zone_grid(
    min_lon: float = Query(...),
    min_lat: float = Query(...),
    max_lon: float = Query(...),
    max_lat: float = Query(...),
    cell_size_km: float = Query(5.0, gt=0, le=100),
) -> dict:
    """
    Generate and severity-score a grid over the given bbox. Each call
    creates a new `grid_run_id` batch rather than overwriting previous
    runs, so historical severity snapshots are preserved (useful once
    Week 3-4's demand model wants to compare how a zone's priority
    changed over time).
    """
    if (max_lon - min_lon) * (max_lat - min_lat) <= 0:
        raise HTTPException(status_code=422, detail="Invalid bounding box")

    grid_run_id = await generate_and_score_grid(min_lon, min_lat, max_lon, max_lat, cell_size_km)
    cell_count = await GridCell.find(GridCell.grid_run_id == grid_run_id).count()

    return {"grid_run_id": grid_run_id, "cell_count": cell_count}


@router.get("")
async def list_zones(
    grid_run_id: str = Query(...),
    min_severity: float = Query(0, ge=0, le=100),
    limit: int = Query(500, le=5000),
) -> list[dict]:
    cells = (
        await GridCell.find(
            GridCell.grid_run_id == grid_run_id,
            GridCell.severity_score >= min_severity,
        )
        .sort(-GridCell.severity_score)
        .limit(limit)
        .to_list()
    )
    return [
        {
            "id": str(c.id),
            "row": c.row,
            "col": c.col,
            "severity_score": c.severity_score,
            "event_component": c.event_component,
            "building_component": c.building_component,
            "population_component": c.population_component,
            "resource_component": c.resource_component,
            "building_count": c.building_count,
            "nearest_resource_km": c.nearest_resource_km,
        }
        for c in cells
    ]


@router.get("/geojson")
async def zones_geojson(grid_run_id: str = Query(...), min_severity: float = Query(0, ge=0, le=100)) -> dict:
    """GeoJSON FeatureCollection with `severity_score` in each feature's
    properties — drop directly into a Leaflet choropleth layer."""
    cells = await GridCell.find(
        GridCell.grid_run_id == grid_run_id,
        GridCell.severity_score >= min_severity,
    ).to_list()

    features = [
        {
            "type": "Feature",
            "geometry": c.geometry,
            "properties": {
                "id": str(c.id),
                "severity_score": c.severity_score,
                "event_component": c.event_component,
                "building_component": c.building_component,
                "population_component": c.population_component,
                "resource_component": c.resource_component,
                "building_count": c.building_count,
                "nearest_resource_km": c.nearest_resource_km,
            },
        }
        for c in cells
    ]

    return {"type": "FeatureCollection", "features": features}

"""
Grid-cell generation + severity scoring — Milestone 1's deliverable.

⚠️ HONESTY NOTE, same spirit as Day 6's impact-extent estimates: the
severity formula below (`score_cell`) is a transparent, capped
weighted-sum heuristic built from whatever signals are actually
available in this system so far (event proximity/alert level, building
density, population exposure, resource-depot distance) — not a
validated humanitarian-need model. It's meant to produce a reasonable,
explainable priority ranking across cells for the dashboard to render
today, with each component stored separately on the GridCell (see the
model) specifically so the weights/formula can be tuned or replaced
later without losing the underlying inputs. Weeks 3-4's demand
prediction model is where a rigorously-fit model belongs.

Geometry: cells are generated with the same equirectangular
(per-axis degrees-per-km) approximation as Day 6's impact-extent
circles — fine at the regional scale this operates at, using the
bounding box's mid-latitude for the lon-degree/km conversion across the
whole grid (a further simplification: this is exact only along that one
latitude, cells drift slightly narrower/wider moving north/south within
a large bbox — negligible for city/district-scale grids).
"""

import math
import uuid
from typing import Any

from app.models.building_footprint import BuildingFootprint
from app.models.disaster_event import DisasterEvent
from app.models.grid_cell import GridCell
from app.models.resource_inventory import ResourceInventory
from app.services.impact.extent_calculator import estimate_impact_radius_km

KM_PER_DEG_LAT = 111.32
EARTH_RADIUS_KM = 6371.0

_ALERT_WEIGHTS = {"Red": 30.0, "Orange": 15.0, "Green": 5.0}


def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    lon1r, lat1r, lon2r, lat2r = map(math.radians, (lon1, lat1, lon2, lat2))
    dlon, dlat = lon2r - lon1r, lat2r - lat1r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1r) * math.cos(lat2r) * math.sin(dlon / 2) ** 2
    return 2 * math.asin(math.sqrt(a)) * EARTH_RADIUS_KM


def _point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    """Standard even-odd ray-casting point-in-polygon test — avoids a
    hard shapely dependency for this one check (shapely's already used
    elsewhere in the project, but this keeps grid scoring self-contained
    and easy to unit test in isolation)."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-15) + xi):
            inside = not inside
        j = i
    return inside


def generate_grid(
    min_lon: float, min_lat: float, max_lon: float, max_lat: float, cell_size_km: float = 5.0
) -> list[dict[str, Any]]:
    """
    Build (but don't persist) grid cells covering the bbox. Returns a
    list of dicts with row/col/geometry/centroid — ready to feed into
    `score_cell` and then `GridCell(**...)`.
    """
    mid_lat = (min_lat + max_lat) / 2
    km_per_deg_lon = KM_PER_DEG_LAT * math.cos(math.radians(mid_lat))
    if abs(km_per_deg_lon) < 1e-6:
        km_per_deg_lon = 1e-6

    lat_step = cell_size_km / KM_PER_DEG_LAT
    lon_step = cell_size_km / km_per_deg_lon

    cells = []
    row = 0
    lat = min_lat
    while lat < max_lat:
        col = 0
        lon = min_lon
        next_lat = min(lat + lat_step, max_lat)
        while lon < max_lon:
            next_lon = min(lon + lon_step, max_lon)
            ring = [[lon, lat], [next_lon, lat], [next_lon, next_lat], [lon, next_lat], [lon, lat]]
            centroid_lon = (lon + next_lon) / 2
            centroid_lat = (lat + next_lat) / 2

            cells.append(
                {
                    "row": row,
                    "col": col,
                    "geometry": {"type": "Polygon", "coordinates": [ring]},
                    "centroid_lon": centroid_lon,
                    "centroid_lat": centroid_lat,
                }
            )
            lon = next_lon
            col += 1
        lat = next_lat
        row += 1

    return cells


def score_cell(
    centroid_lon: float,
    centroid_lat: float,
    cell_ring: list[list[float]],
    events: list[DisasterEvent],
    buildings: list[BuildingFootprint],
    resources: list[ResourceInventory],
) -> dict[str, Any]:
    """
    Compute a cell's severity score and its components. See module
    docstring for the honesty caveat on this being an illustrative
    heuristic, not a validated model.
    """
    # --- Event component (capped at 60) ---
    event_component = 0.0
    max_population = 0
    contributing_ids: list[str] = []
    for event in events:
        if event.location is None:
            continue
        ev_lon, ev_lat = event.location.coordinates
        dist_km = haversine_km(centroid_lon, centroid_lat, ev_lon, ev_lat)
        radius_km = estimate_impact_radius_km(event.event_type, event.severity_value, event.alert_level)
        if dist_km <= radius_km:
            weight = _ALERT_WEIGHTS.get(event.alert_level or "", 5.0)
            event_component += weight * (1 - dist_km / radius_km)
            contributing_ids.append(str(event.id))
            if event.population_exposed:
                max_population = max(max_population, event.population_exposed)
    event_component = min(event_component, 60.0)

    # --- Building density component (capped at 20) ---
    building_count = sum(1 for b in buildings if _point_in_ring(*_geometry_reference_point(b.geometry), cell_ring))
    building_component = min(building_count / 20.0 * 20.0, 20.0)

    # --- Population component (capped at 20) — proxy from event data only,
    #     not a true per-cell census; see module docstring. ---
    population_component = min(math.log10(max_population + 1) * 5.0, 20.0) if max_population else 0.0

    # --- Resource-distance component (capped at 20; farther = higher need) ---
    nearest_resource_km = None
    if resources:
        nearest_resource_km = min(
            haversine_km(centroid_lon, centroid_lat, *r.location.coordinates) for r in resources
        )
        resource_component = min(nearest_resource_km / 50.0 * 20.0, 20.0)
    else:
        resource_component = 10.0  # no resources known at all -> moderate-high default need

    total = event_component + building_component + population_component + resource_component

    return {
        "severity_score": round(min(total, 100.0), 2),
        "event_component": round(event_component, 2),
        "building_component": round(building_component, 2),
        "population_component": round(population_component, 2),
        "resource_component": round(resource_component, 2),
        "contributing_event_ids": contributing_ids,
        "building_count": building_count,
        "nearest_resource_km": round(nearest_resource_km, 2) if nearest_resource_km is not None else None,
    }


def _geometry_reference_point(geometry: dict) -> tuple[float, float]:
    """A representative (lon, lat) for a building's geometry — its first
    vertex for Polygons, or the point itself. Good enough for a
    density count; not the true centroid, but avoids pulling in
    shapely just for this one internal check."""
    if geometry["type"] == "Point":
        return tuple(geometry["coordinates"])
    return tuple(geometry["coordinates"][0][0])


async def generate_and_score_grid(
    min_lon: float, min_lat: float, max_lon: float, max_lat: float, cell_size_km: float = 5.0
) -> str:
    """
    Full Day 10 pipeline: generate cells, pull current events/buildings/
    resources within the bbox, score every cell, persist as GridCell
    documents under one `grid_run_id`. Returns that run id.
    """
    grid_run_id = str(uuid.uuid4())

    raw_cells = generate_grid(min_lon, min_lat, max_lon, max_lat, cell_size_km)

    events = await DisasterEvent.find(
        DisasterEvent.is_current == True,  # noqa: E712
        {
            "location.coordinates.0": {"$gte": min_lon - 2, "$lte": max_lon + 2},
            "location.coordinates.1": {"$gte": min_lat - 2, "$lte": max_lat + 2},
        },
    ).to_list()

    buildings = await BuildingFootprint.find().to_list()  # bbox pre-filtering left to Day 8's /buildings/ingest scope
    resources = await ResourceInventory.find().to_list()

    docs = []
    for cell in raw_cells:
        scoring = score_cell(
            cell["centroid_lon"],
            cell["centroid_lat"],
            cell["geometry"]["coordinates"][0],
            events,
            buildings,
            resources,
        )
        docs.append(
            GridCell(
                grid_run_id=grid_run_id,
                row=cell["row"],
                col=cell["col"],
                geometry=cell["geometry"],
                centroid={"type": "Point", "coordinates": [cell["centroid_lon"], cell["centroid_lat"]]},
                severity_score=scoring["severity_score"],
                event_component=scoring["event_component"],
                building_component=scoring["building_component"],
                population_component=scoring["population_component"],
                resource_component=scoring["resource_component"],
                contributing_event_ids=scoring["contributing_event_ids"],
                building_count=scoring["building_count"],
                nearest_resource_km=scoring["nearest_resource_km"],
            )
        )

    if docs:
        await GridCell.insert_many(docs)

    return grid_run_id

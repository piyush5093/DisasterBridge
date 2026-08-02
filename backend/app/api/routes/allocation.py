"""
Resource Allocation API Routes
POST /api/allocation/optimize       — optimize resources for a zone
POST /api/allocation/optimize-all   — optimize resources for ALL active zones
GET  /api/allocation/routes         — get routing info depot→zone
GET  /api/allocation/status         — optimizer health check
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.db.database import get_db
from app.models.zone import DisasterZone
from app.models.resource import Resource
from app.models.depot import Depot
from app.services.resource_optimizer import optimizer

router = APIRouter()


@router.get("/status")
def optimizer_status():
    """Health check for the optimizer service."""
    return {
        "optimizer":   "online",
        "algorithm":   "greedy_haversine",
        "version":     "1.0",
        "description": "Priority-weighted greedy allocator with Haversine distance routing.",
        "avg_truck_speed_kph": 60.0,
    }


@router.post("/optimize")
def optimize_zone(
    zone_id: int,
    db: Session = Depends(get_db),
):
    """
    POST /api/allocation/optimize?zone_id={id}
    Compute an optimal resource allocation plan for the given zone.
    Returns which depot to dispatch from, estimated travel time,
    and per-category resource quantities.
    """
    zone = db.query(DisasterZone).filter(
        DisasterZone.id == zone_id, DisasterZone.is_active == 1
    ).first()
    if not zone:
        raise HTTPException(status_code=404, detail=f"Active zone {zone_id} not found")

    depots    = db.query(Depot).filter(Depot.is_active == 1).all()
    resources = db.query(Resource).all()

    if not depots:
        raise HTTPException(status_code=503, detail="No active depots in system")

    plan = optimizer.allocate_single_zone(zone, depots, resources)

    return {
        "status":           "ok",
        "allocation_plan":  plan.to_dict(),
    }


@router.post("/optimize-all")
def optimize_all_zones(
    severity_filter: Optional[str] = Query(
        None, description="Only allocate for zones of this severity: critical/high/medium/low"
    ),
    db: Session = Depends(get_db),
):
    """
    POST /api/allocation/optimize-all
    Compute allocation plans for all active zones (sorted by severity priority).
    Optionally filter to a specific severity level.
    """
    query = db.query(DisasterZone).filter(DisasterZone.is_active == 1)
    if severity_filter:
        query = query.filter(DisasterZone.severity == severity_filter.lower())

    zones = query.order_by(DisasterZone.severity_score.desc()).all()
    if not zones:
        return {"status": "ok", "message": "No matching zones found", "plans": []}

    depots    = db.query(Depot).filter(Depot.is_active == 1).all()
    resources = db.query(Resource).all()

    if not depots:
        raise HTTPException(status_code=503, detail="No active depots in system")

    plans = optimizer.allocate_all_zones(zones, depots, resources)

    feasible   = sum(1 for p in plans if p.feasible)
    infeasible = len(plans) - feasible

    return {
        "status":           "ok",
        "total_zones":      len(zones),
        "feasible_plans":   feasible,
        "infeasible_plans": infeasible,
        "plans":            [p.to_dict() for p in plans],
    }


@router.get("/routes")
def get_route(
    zone_id:  int = Query(..., description="Destination zone ID"),
    depot_id: int = Query(..., description="Source depot ID"),
    db: Session = Depends(get_db),
):
    """
    GET /api/allocation/routes?zone_id=1&depot_id=2
    Returns point-to-point routing info (distance, ETA) between a depot and a zone.
    Uses Haversine straight-line distance as a proxy for road distance.
    """
    zones  = db.query(DisasterZone).all()
    depots = db.query(Depot).all()

    route = optimizer.get_optimal_routing(zone_id, depot_id, depots, zones)

    if not route.get("feasible", True) and "error" in route:
        raise HTTPException(status_code=404, detail=route["error"])

    return route


@router.get("/nearest-depot")
def get_nearest_depot(
    zone_id: int = Query(..., description="Zone ID to find nearest depot for"),
    db: Session = Depends(get_db),
):
    """
    GET /api/allocation/nearest-depot?zone_id=1
    Returns the nearest active depot to a given disaster zone.
    """
    zone = db.query(DisasterZone).filter(DisasterZone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone {zone_id} not found")

    depots = db.query(Depot).filter(Depot.is_active == 1).all()
    if not depots:
        raise HTTPException(status_code=503, detail="No active depots")

    from app.services.resource_optimizer import haversine_km
    depots_with_dist = [
        {
            "depot_id":    d.id,
            "depot_name":  d.name,
            "city":        d.city,
            "state":       d.state,
            "distance_km": round(haversine_km(zone.latitude, zone.longitude, d.latitude, d.longitude), 2),
            "estimated_hours": round(
                haversine_km(zone.latitude, zone.longitude, d.latitude, d.longitude) / 60.0, 2
            ),
        }
        for d in depots
    ]
    depots_with_dist.sort(key=lambda x: x["distance_km"])

    return {
        "zone_id":   zone.id,
        "zone_name": zone.name,
        "nearest":   depots_with_dist[0],
        "all_depots_sorted": depots_with_dist,
    }

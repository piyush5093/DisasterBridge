"""
Disaster Zones API Routes
GET /api/zones          — list all active zones
GET /api/zones/{id}     — get single zone
POST /api/zones         — create zone manually
PUT /api/zones/{id}     — update zone
DELETE /api/zones/{id}  — deactivate zone
GET /api/zones/summary  — dashboard summary stats
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.models.zone import DisasterZone, SeverityLevel
from app.schemas.zone import ZoneCreate, ZoneUpdate, ZoneResponse
from app.services.demand_predictor import predict_demand, predictor

router = APIRouter()


@router.get("/summary")
def get_zones_summary(db: Session = Depends(get_db)):
    """Dashboard stat cards data."""
    zones = db.query(DisasterZone).filter(DisasterZone.is_active == 1).all()

    total_affected  = sum(z.population_affected for z in zones)
    critical_count  = sum(1 for z in zones if z.severity == SeverityLevel.CRITICAL)
    high_count      = sum(1 for z in zones if z.severity == SeverityLevel.HIGH)
    medium_count    = sum(1 for z in zones if z.severity == SeverityLevel.MEDIUM)
    low_count       = sum(1 for z in zones if z.severity == SeverityLevel.LOW)

    return {
        "total_zones":        len(zones),
        "total_affected":     total_affected,
        "severity_breakdown": {
            "critical": critical_count,
            "high":     high_count,
            "medium":   medium_count,
            "low":      low_count,
        },
        "zones_by_state": _group_by_state(zones),
    }


@router.get("/", response_model=List[ZoneResponse])
def list_zones(
    severity: Optional[str] = Query(None, description="Filter by severity: critical/high/medium/low"),
    state:    Optional[str] = Query(None, description="Filter by state name"),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    query = db.query(DisasterZone)
    if active_only:
        query = query.filter(DisasterZone.is_active == 1)
    if severity:
        query = query.filter(DisasterZone.severity == severity.lower())
    if state:
        query = query.filter(DisasterZone.state.ilike(f"%{state}%"))
    return query.order_by(DisasterZone.severity_score.desc()).all()


@router.get("/{zone_id}", response_model=ZoneResponse)
def get_zone(zone_id: int, db: Session = Depends(get_db)):
    zone = db.query(DisasterZone).filter(DisasterZone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone {zone_id} not found")
    return zone


@router.get("/{zone_id}/demand")
def get_zone_demand(zone_id: int, db: Session = Depends(get_db)):
    """
    GET /api/zones/{id}/demand
    Returns ML-predicted resource demand for a disaster zone.
    Predictions: food_packets, water_liters, medical_kits,
                 shelter_capacity, rescue_vehicles, personnel_needed.
    """
    zone = db.query(DisasterZone).filter(DisasterZone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone {zone_id} not found")

    demand = predict_demand(zone)

    return {
        "zone_id":    zone_id,
        "zone_name":  zone.name,
        "severity":   zone.severity,
        "population_affected": zone.population_affected,
        "demand":     demand,
        "model_ready": predictor.is_ready(),
    }


@router.get("/predictor/status")
def get_predictor_status():
    """Check if the ML demand prediction model is loaded and ready."""
    return {
        "model_ready": predictor.is_ready(),
        "model_path":  str(predictor._pipeline.__class__.__name__) if predictor.is_ready() else None,
        "features":    predictor._features,
        "targets":     predictor._targets,
        "error":       predictor._load_error,
    }


@router.post("/", response_model=ZoneResponse, status_code=201)
def create_zone(payload: ZoneCreate, db: Session = Depends(get_db)):
    zone = DisasterZone(**payload.model_dump())
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


@router.put("/{zone_id}", response_model=ZoneResponse)
def update_zone(zone_id: int, payload: ZoneUpdate, db: Session = Depends(get_db)):
    zone = db.query(DisasterZone).filter(DisasterZone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone {zone_id} not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(zone, field, value)
    db.commit()
    db.refresh(zone)
    return zone


@router.delete("/{zone_id}")
def deactivate_zone(zone_id: int, db: Session = Depends(get_db)):
    zone = db.query(DisasterZone).filter(DisasterZone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone {zone_id} not found")
    zone.is_active = 0
    db.commit()
    return {"message": f"Zone {zone_id} deactivated", "id": zone_id}


def _group_by_state(zones):
    result = {}
    for z in zones:
        result.setdefault(z.state, 0)
        result[z.state] += 1
    return result

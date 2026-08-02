"""
Resources API Routes
GET /api/resources              — list all resources
GET /api/resources/summary      — inventory overview (for dashboard cards)
GET /api/resources/{id}         — single resource
POST /api/resources             — add resource
PUT /api/resources/{id}         — update quantities
GET /api/resources/alerts       — resources below critical threshold
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.models.resource import Resource
from app.schemas.resource import ResourceCreate, ResourceUpdate, ResourceResponse

router = APIRouter()


@router.get("/summary")
def get_resource_summary(db: Session = Depends(get_db)):
    """Inventory overview grouped by category (for dashboard resource cards)."""
    resources = db.query(Resource).all()
    summary   = {}

    for r in resources:
        cat = r.category
        if cat not in summary:
            summary[cat] = {"total": 0, "available": 0, "deployed": 0, "items": []}
        summary[cat]["total"]    += r.quantity_total
        summary[cat]["available"]+= r.quantity_available
        summary[cat]["deployed"] += r.quantity_deployed
        summary[cat]["items"].append({
            "id":        r.id,
            "name":      r.name,
            "available": r.quantity_available,
            "total":     r.quantity_total,
            "unit":      r.unit,
            "pct":       _pct(r.quantity_available, r.quantity_total),
            "critical":  r.is_critical(),
        })

    return {"categories": summary, "total_items": len(resources)}


@router.get("/alerts")
def get_resource_alerts(db: Session = Depends(get_db)):
    """Resources that are below their critical threshold — needs attention."""
    resources = db.query(Resource).all()
    critical  = [r for r in resources if r.is_critical()]
    return {
        "count":     len(critical),
        "resources": [
            {
                "id":        r.id,
                "name":      r.name,
                "category":  r.category,
                "available": r.quantity_available,
                "total":     r.quantity_total,
                "pct":       _pct(r.quantity_available, r.quantity_total),
                "threshold": r.critical_threshold,
            }
            for r in critical
        ],
    }


@router.get("/", response_model=List[ResourceResponse])
def list_resources(
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Resource)
    if category:
        query = query.filter(Resource.category == category.lower())
    return query.all()


@router.get("/{resource_id}", response_model=ResourceResponse)
def get_resource(resource_id: int, db: Session = Depends(get_db)):
    r = db.query(Resource).filter(Resource.id == resource_id).first()
    if not r:
        raise HTTPException(status_code=404, detail=f"Resource {resource_id} not found")
    return r


@router.post("/", response_model=ResourceResponse, status_code=201)
def create_resource(payload: ResourceCreate, db: Session = Depends(get_db)):
    r = Resource(**payload.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.put("/{resource_id}", response_model=ResourceResponse)
def update_resource(resource_id: int, payload: ResourceUpdate, db: Session = Depends(get_db)):
    r = db.query(Resource).filter(Resource.id == resource_id).first()
    if not r:
        raise HTTPException(status_code=404, detail=f"Resource {resource_id} not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(r, field, value)
    db.commit()
    db.refresh(r)
    return r


def _pct(available: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(available / total * 100, 1)

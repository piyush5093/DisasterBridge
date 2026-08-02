"""
Disaster Events API Routes
GET /api/events/        — list raw ingested disaster events
GET /api/events/{id}    — single event detail
DELETE /api/events/{id} — remove stale event
GET /api/events/stats   — aggregate source stats
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.models.event import DisasterEvent
from app.schemas.event import EventResponse

router = APIRouter()


@router.get("/stats")
def get_event_stats(db: Session = Depends(get_db)):
    """Aggregate stats per source — useful for the feed monitor panel."""
    events = db.query(DisasterEvent).all()
    stats: dict = {}
    for e in events:
        src = e.source or "unknown"
        if src not in stats:
            stats[src] = {"count": 0, "types": {}, "linked_zones": 0}
        stats[src]["count"] += 1
        dtype = e.disaster_type or "unknown"
        stats[src]["types"][dtype] = stats[src]["types"].get(dtype, 0) + 1
        if e.zone_id:
            stats[src]["linked_zones"] += 1

    return {
        "total_events": len(events),
        "by_source": stats,
    }


@router.get("/", response_model=List[EventResponse])
def list_events(
    source: Optional[str] = Query(None, description="gdacs / usgs / ndma"),
    disaster_type: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    """List raw disaster events stored from feed ingestion."""
    query = db.query(DisasterEvent)
    if source:
        query = query.filter(DisasterEvent.source == source.lower())
    if disaster_type:
        query = query.filter(DisasterEvent.disaster_type == disaster_type.lower())
    return query.order_by(DisasterEvent.fetched_at.desc()).limit(limit).all()


@router.get("/{event_id}", response_model=EventResponse)
def get_event(event_id: int, db: Session = Depends(get_db)):
    """Retrieve a single raw event by ID."""
    ev = db.query(DisasterEvent).filter(DisasterEvent.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    return ev


@router.delete("/{event_id}")
def delete_event(event_id: int, db: Session = Depends(get_db)):
    """Remove a stale/duplicate event record."""
    ev = db.query(DisasterEvent).filter(DisasterEvent.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    db.delete(ev)
    db.commit()
    return {"message": f"Event {event_id} deleted", "id": event_id}

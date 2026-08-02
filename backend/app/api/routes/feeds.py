"""
Live Feeds API Routes
GET /api/feeds/live      — Combined GDACS + USGS live summary
GET /api/feeds/gdacs     — GDACS India events
GET /api/feeds/usgs      — USGS India earthquakes
POST /api/feeds/classify — Fetch + classify events → create DisasterZones in DB
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.zone import DisasterZone
from app.models.event import DisasterEvent
from app.services.zone_classifier import classify_gdacs_event, classify_usgs_event

router = APIRouter()


@router.get("/live")
def get_live_feed():
    """
    Fetch combined GDACS + USGS live disaster feed for India.
    No DB write — just returns raw + quick summary.
    """
    try:
        from data_ingestion.connectors.gdacs_connector import gdacs
        from data_ingestion.connectors.usgs_connector  import usgs

        gdacs_events = gdacs.fetch_all_india()
        usgs_events  = usgs.fetch_recent()
        usgs_summary = usgs.get_summary(usgs_events)

        return {
            "status": "live",
            "gdacs":  {
                "count":  len(gdacs_events),
                "events": gdacs_events[:20],
            },
            "usgs": {
                "count":   usgs_summary["count"],
                "summary": usgs_summary,
                "events":  usgs_events[:20],
            },
            "total_events": len(gdacs_events) + usgs_summary["count"],
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Feed fetch failed: {str(e)}")


@router.get("/gdacs")
def get_gdacs_feed():
    """Fetch GDACS India events only."""
    try:
        from data_ingestion.connectors.gdacs_connector import gdacs
        events = gdacs.fetch_all_india()
        return {"source": "GDACS", "count": len(events), "events": events}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"GDACS fetch failed: {str(e)}")


@router.get("/usgs")
def get_usgs_feed():
    """Fetch USGS India earthquakes only."""
    try:
        from data_ingestion.connectors.usgs_connector import usgs
        events  = usgs.fetch_significant()
        summary = usgs.get_summary(events)
        return {"source": "USGS", "summary": summary, "events": events}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"USGS fetch failed: {str(e)}")


@router.post("/classify")
def classify_and_save(db: Session = Depends(get_db)):
    """
    Fetch events from GDACS + USGS, classify them into disaster zones,
    and save new zones to the database.
    """
    try:
        from data_ingestion.connectors.gdacs_connector import gdacs
        from data_ingestion.connectors.usgs_connector  import usgs

        created_zones = []
        errors        = []

        # ── GDACS ───────────────────────────────────────────────────────────
        gdacs_events = gdacs.fetch_all_india()
        for event in gdacs_events:
            try:
                zone_data = classify_gdacs_event(event)
                if not zone_data:
                    continue

                # Avoid duplicates by source_event_id
                existing = db.query(DisasterZone).filter(
                    DisasterZone.source_event_id == zone_data["source_event_id"],
                    DisasterZone.source == "gdacs"
                ).first()
                if existing:
                    continue

                zone = DisasterZone(**zone_data)
                db.add(zone)
                created_zones.append(zone_data["name"])
            except Exception as e:
                errors.append(f"GDACS zone error: {e}")

        # ── USGS ────────────────────────────────────────────────────────────
        usgs_features = usgs.fetch_recent()
        for feature in usgs_features:
            try:
                zone_data = classify_usgs_event(feature)
                if not zone_data:
                    continue

                existing = db.query(DisasterZone).filter(
                    DisasterZone.source_event_id == zone_data["source_event_id"],
                    DisasterZone.source == "usgs"
                ).first()
                if existing:
                    continue

                zone = DisasterZone(**zone_data)
                db.add(zone)
                created_zones.append(zone_data["name"])
            except Exception as e:
                errors.append(f"USGS zone error: {e}")

        db.commit()

        return {
            "status":        "success",
            "zones_created": len(created_zones),
            "zones":         created_zones,
            "errors":        errors,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")

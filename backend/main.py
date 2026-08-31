from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import engine, Base, get_db
import services
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional
from auth import (
    hash_password, verify_password, create_access_token, get_current_commander
)

app = FastAPI(title="Disaster Bridge API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Startup: create tables and seed default commanders ──────────────────────────
@app.on_event("startup")
def on_startup():
    from models import Commander
    Base.metadata.create_all(bind=engine)

    db = next(get_db())
    try:
        # Only seed if table is empty — safe to run on every restart
        if db.query(Commander).count() == 0:
            default_commanders = [
                Commander(
                    full_name="Commander Kamin",
                    email="kamin@disasterbridge.com",
                    password_hash=hash_password("commander123"),
                    role="admin",
                    is_active=True,
                ),
                Commander(
                    full_name="Field Commander Sharma",
                    email="sharma@disasterbridge.com",
                    password_hash=hash_password("fieldops456"),
                    role="commander",
                    is_active=True,
                ),
                Commander(
                    full_name="Admin Ops",
                    email="admin@disasterbridge.com",
                    password_hash=hash_password("admin789"),
                    role="admin",
                    is_active=True,
                ),
            ]
            for c in default_commanders:
                db.add(c)
            db.commit()
            print(f"[AUTH] Seeded {len(default_commanders)} default commanders.")
        else:
            print(f"[AUTH] Commanders table already has data — skipping seed.")
    finally:
        db.close()


# ── Auth endpoints ──────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str

class CommanderOut(BaseModel):
    id: str
    full_name: str
    email: str
    role: str

    class Config:
        from_attributes = True

@app.post("/api/auth/login", tags=["auth"])
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Accepts {email, password}. Returns a signed JWT access_token on success,
    or 401 on bad credentials. The token is valid for 8 hours.
    """
    from models import Commander
    commander = db.query(Commander).filter(
        Commander.email == payload.email.strip().lower(),
        Commander.is_active == True,
    ).first()

    if not commander or not verify_password(payload.password, commander.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token({"sub": str(commander.id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "commander": {
            "id": str(commander.id),
            "full_name": commander.full_name,
            "email": commander.email,
            "role": commander.role,
        },
    }

@app.get("/api/auth/me", tags=["auth"])
def get_me(current: object = Depends(get_current_commander)):
    """
    Returns the currently authenticated commander's profile.
    Requires a valid Bearer token in the Authorization header.
    """
    return {
        "id": str(current.id),
        "full_name": current.full_name,
        "email": current.email,
        "role": current.role,
    }

@app.post("/api/auth/logout", tags=["auth"])
def logout():
    """
    JWT is stateless — actual invalidation happens client-side by deleting the token.
    This endpoint is a clean hook for future server-side token blacklisting.
    """
    return {"ok": True, "message": "Logged out successfully"}


# ── Commander management (admin-only) ──────────────────────────────────────────
class CreateCommanderRequest(BaseModel):
    full_name: str
    email: str
    password: str
    role: str = "commander"   # 'commander' | 'admin'

def require_admin(current=Depends(get_current_commander)):
    """Dependency that raises 403 if the caller is not an admin."""
    if current.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current

@app.get("/api/commanders", tags=["commanders"])
def list_commanders(
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    """List all commanders (admin only). Returns active and inactive accounts."""
    from models import Commander
    commanders = db.query(Commander).order_by(Commander.created_at).all()
    return [
        {
            "id": str(c.id),
            "full_name": c.full_name,
            "email": c.email,
            "role": c.role,
            "is_active": c.is_active,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in commanders
    ]

@app.post("/api/commanders", tags=["commanders"])
def create_commander(
    payload: CreateCommanderRequest,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    """Create a new commander account (admin only)."""
    from models import Commander
    # Check for duplicate email
    existing = db.query(Commander).filter(
        Commander.email == payload.email.strip().lower()
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A commander with this email already exists",
        )
    new_commander = Commander(
        full_name=payload.full_name.strip(),
        email=payload.email.strip().lower(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(new_commander)
    db.commit()
    db.refresh(new_commander)
    return {
        "id": str(new_commander.id),
        "full_name": new_commander.full_name,
        "email": new_commander.email,
        "role": new_commander.role,
        "is_active": new_commander.is_active,
    }

@app.delete("/api/commanders/{commander_id}", tags=["commanders"])
def deactivate_commander(
    commander_id: str,
    db: Session = Depends(get_db),
    current: object = Depends(require_admin),
):
    """
    Deactivate a commander account (admin only).
    Soft-delete only — sets is_active=False. Cannot deactivate yourself.
    """
    from models import Commander
    import uuid as _uuid
    if str(current.id) == commander_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )
    target = db.query(Commander).filter(
        Commander.id == _uuid.UUID(commander_id)
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="Commander not found")
    target.is_active = False
    db.commit()
    return {"ok": True, "deactivated": commander_id}

@app.patch("/api/commanders/{commander_id}/reactivate", tags=["commanders"])
def reactivate_commander(
    commander_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    """Re-activate a previously deactivated commander (admin only)."""
    from models import Commander
    import uuid as _uuid
    target = db.query(Commander).filter(
        Commander.id == _uuid.UUID(commander_id)
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="Commander not found")
    target.is_active = True
    db.commit()
    return {"ok": True, "reactivated": commander_id}

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Checks live DB connectivity (`SELECT 1`) and returns {"status": "ok", "db": "connected"}.
    Must actually fail loudly if DB is down.
    """
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

@app.post("/api/ingest/gdacs/sync")
def sync_gdacs(db: Session = Depends(get_db)):
    """
    Triggers a sync of the live GDACS RSS/GeoJSON feed.
    """
    result = services.fetch_gdacs_events(db)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.post("/api/ingest/usgs/sync")
def sync_usgs(db: Session = Depends(get_db)):
    """
    Triggers a sync of the live USGS Earthquake GeoJSON feed.
    """
    result = services.fetch_usgs_events(db)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.post("/api/ingest/ndma/sync")
def sync_ndma(db: Session = Depends(get_db)):
    result = services.fetch_ndma_events(db)
    return result

@app.post("/api/events/{event_id}/compute-impact-extent")
def compute_impact(event_id: str, db: Session = Depends(get_db)):
    res = services.compute_impact_extent(db, event_id)
    if "error" in res: raise HTTPException(status_code=404, detail=res["error"])
    return res

@app.post("/api/events/{event_id}/compute-population-exposure")
def compute_population(event_id: str, db: Session = Depends(get_db)):
    res = services.compute_population_exposure(db, event_id)
    if "error" in res: raise HTTPException(status_code=404, detail=res["error"])
    return res

@app.post("/api/events/{event_id}/compute-building-footprint")
def compute_buildings(event_id: str, db: Session = Depends(get_db)):
    res = services.compute_building_footprint(db, event_id)
    if "error" in res: raise HTTPException(status_code=404, detail=res["error"])
    return res

@app.get("/api/events/{event_id}/satellite-imagery")
def get_imagery(event_id: str, db: Session = Depends(get_db)):
    res = services.get_satellite_imagery(event_id, db)
    if "error" in res: raise HTTPException(status_code=404, detail=res["error"])
    return res

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

import services_phase3
from pydantic import BaseModel

class ResourcePayload(BaseModel):
    resource_type: str
    quantity: float
    unit: str
    lat: float
    lng: float
    depot_name: str
    status: str = "available"

@app.post("/api/resources")
def create_resource(payload: ResourcePayload, db: Session = Depends(get_db)):
    return services_phase3.create_resource(db, payload.dict())

@app.get("/api/resources/near")
def get_resources_near(lat: float, lng: float, radius_km: float, db: Session = Depends(get_db)):
    return services_phase3.get_resources_near(db, lat, lng, radius_km)

@app.post("/api/zones/classify")
def classify_zones(event_id: str, db: Session = Depends(get_db)):
    res = services_phase3.classify_zones(db, event_id)
    if "error" in res: raise HTTPException(status_code=400, detail=res["error"])
    return res


import services_ml
import services_logistics

class PredictionPayload(BaseModel):
    vulnerability_demographics: dict = {"elderly": 0.3, "children": 0.2, "medically_dependent": 0.1}

@app.post("/predict/demand/{zone_id}")
def predict_demand(zone_id: str, payload: PredictionPayload, db: Session = Depends(get_db)):
    res = services_ml.predict_demand_for_zone(db, zone_id, payload.vulnerability_demographics)
    if "error" in res: raise HTTPException(status_code=400, detail=res["error"])
    return res

class RecalibratePayload(BaseModel):
    new_severity: float
    reason: str

@app.post("/api/predictions/{zone_id}/recalibrate")
def recalibrate_prediction(zone_id: str, payload: RecalibratePayload, db: Session = Depends(get_db)):
    res = services_ml.recalibrate_prediction(db, zone_id, payload.new_severity, payload.reason)
    if "error" in res: raise HTTPException(status_code=400, detail=res["error"])
    return res

@app.post("/api/predictions/simulate")
def simulate_scenario(zone_id: str, severity_delta: float, db: Session = Depends(get_db)):
    res = services_ml.simulate_scenario(db, zone_id, severity_delta)
    if "error" in res: raise HTTPException(status_code=400, detail=res["error"])
    return res

@app.post("/api/allocation/optimize")
def optimize_allocation(zone_id: str, db: Session = Depends(get_db)):
    res = services_logistics.optimize_allocation(db, zone_id)
    if "error" in res: raise HTTPException(status_code=400, detail=res["error"])
    return res

@app.post("/api/allocation/optimize-with-routes")
def optimize_with_routes(plan_run_id: str, db: Session = Depends(get_db)):
    res = services_logistics.generate_routes_for_plan(db, plan_run_id)
    if "error" in res: raise HTTPException(status_code=400, detail=res["error"])
    return res

@app.post("/api/missions/create-from-plan")
def create_missions_from_plan(plan_run_id: str, db: Session = Depends(get_db)):
    res = services_logistics.create_missions_for_plan(db, plan_run_id)
    if "error" in res: raise HTTPException(status_code=400, detail=res["error"])
    return res

@app.post("/api/relief-plan/generate")
def generate_unified_plan(zone_id: str, db: Session = Depends(get_db)):
    res = services_logistics.generate_unified_plan(db, zone_id)
    if "error" in res: raise HTTPException(status_code=400, detail=res["error"])
    return res


@app.get("/api/analytics/dashboard-summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    active_incidents = db.execute(text("SELECT count(*) FROM disaster_events")).fetchone()[0]

    # Resources deployed = SUM of actual supplies carried by non-cancelled missions
    supplies_rows = db.execute(text(
        "SELECT supplies FROM missions WHERE status::TEXT != 'cancelled'"
    )).fetchall()
    import json as _json
    resources_deployed = 0
    type_totals: dict = {}
    for (s,) in supplies_rows:
        if s:
            d = s if isinstance(s, dict) else _json.loads(s)
            for k, v in d.items():
                amt = float(v)
                resources_deployed += amt
                type_totals[k] = type_totals.get(k, 0) + amt

    # Active missions = assigned + in_transit (not pending/delivered/cancelled)
    active_missions = db.execute(text(
        "SELECT count(*) FROM missions WHERE status::TEXT IN ('assigned', 'in_transit')"
    )).fetchone()[0]

    people_assisted = db.execute(text(
        "SELECT COALESCE(SUM(population_exposed), 0) FROM disaster_events WHERE alert_level IN ('orange', 'red')"
    )).fetchone()[0]

    # Allocation chart = supplies carried by active (non-cancelled) missions per type.
    # This reflects the CURRENT deployment state, not a stale cumulative sum of all
    # historical plan runs (which grows forever and never resets on cancel).
    UNIT_LABELS = {"food": "packages", "hygiene_kits": "kits", "medical": "kits", "shelter": "units"}
    allocation_chart = [
        {"name": k, "value": round(v, 1), "unit": UNIT_LABELS.get(k, "units")}
        for k, v in sorted(type_totals.items())
    ]

    volunteers_count = db.execute(text("SELECT COUNT(*) FROM volunteers")).scalar() or 0

    return {
        "active_incidents": active_incidents,
        "resources_deployed": int(sum(r.get("value", 0) for r in allocation_chart)),
        "active_missions": active_missions,
        "volunteers": volunteers_count,
        "population_at_risk": int(people_assisted),
        "allocation_chart": allocation_chart
    }

@app.get("/api/dashboard/missions")
def get_dashboard_missions(db: Session = Depends(get_db)):
    rows = db.execute(text('''
        SELECT
            m.id,
            m.team_name,
            m.vehicle_id,
            m.status::TEXT         AS status,
            m.priority::TEXT       AS priority,
            m.supplies,
            m.created_at,
            r.distance_km,
            r.estimated_duration_minutes,
            r.road_status,
            r.is_fallback_straight_line,
            ST_AsGeoJSON(r.route_geometry) AS geom,
            m.zone_id::TEXT        AS zone_id,
            gc.severity_score,
            gc.priority::TEXT      AS zone_priority,
            de.event_type::TEXT    AS event_type,
            de.alert_level::TEXT   AS alert_level,
            ri.depot_name          AS depot_name
        FROM missions m
        JOIN routes r ON m.route_id = r.id
        JOIN grid_cells gc ON m.zone_id = gc.id
        LEFT JOIN disaster_events de ON gc.related_event_id = de.id
        LEFT JOIN resource_items ri ON r.depot_id = ri.id
        ORDER BY m.created_at DESC
    ''')).fetchall()
    import json as _json
    import json as _json
    UNITS = {"food": "packages", "hygiene_kits": "kits", "medical": "kits", "shelter": "units"}
    result = []
    for r in rows:
        supplies_raw = r[5]
        if isinstance(supplies_raw, str):
            try: supplies_raw = _json.loads(supplies_raw)
            except: supplies_raw = {}
        # Build readable supplies string
        sup = supplies_raw or {}
        sup_str = ", ".join(
            f"{float(v):.0f} {UNITS.get(k,'units')} {k}" for k, v in sup.items()
        ) if sup else "No supplies"
        # Parse geometry — extract first coord (depot) and last coord (zone)
        geom_dict = _json.loads(r[11]) if r[11] else None
        depot_lat = depot_lng = zone_lat = zone_lng = None
        if geom_dict and geom_dict.get("type") == "LineString":
            coords = geom_dict.get("coordinates", [])
            if len(coords) >= 2:
                depot_lng, depot_lat = coords[0][0], coords[0][1]
                zone_lng,  zone_lat  = coords[-1][0], coords[-1][1]
        result.append({
            "id":            str(r[0]),
            "team":          r[1],
            "vehicle_id":    r[2],
            "status":        r[3],
            "priority":      r[4],
            "supplies":      sup,
            "supplies_display": sup_str,
            "created_at":    r[6].isoformat() if r[6] else None,
            "distance":      float(r[7]) if r[7] else 0,
            "duration":      float(r[8]) if r[8] else 0,
            "road_status":   str(r[9]) if r[9] else None,
            "fallback":      r[10],
            "geometry":      geom_dict,
            "zone_id":       r[12],
            "severity":      float(r[13]) if r[13] else 0,
            "zone_priority": r[14],
            "event_type":    r[15] or "unknown",
            "alert_level":   r[16] or "unknown",
            "depot_name":    r[17] or "Supply Depot",
            "depot_lat":     depot_lat,
            "depot_lng":     depot_lng,
            "zone_lat":      zone_lat,
            "zone_lng":      zone_lng,
        })
    return result

@app.get("/api/dashboard/events")
def get_dashboard_events(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT id,
               COALESCE(raw_payload->>'title', raw_payload->>'description', 'Disaster Event') AS title,
               source, alert_level,
               ST_X(location::geometry) AS lng,
               ST_Y(location::geometry) AS lat,
               CAST(event_type AS TEXT) AS event_type,
               population_exposed
        FROM disaster_events
        ORDER BY event_time DESC
        LIMIT 2000
    """)).fetchall()
    return [{
        "id": str(r[0]),
        "title": r[1],
        "source": r[2],
        "alert_level": r[3],
        "lng": float(r[4]) if r[4] else 0,
        "lat": float(r[5]) if r[5] else 0,
        "event_type": r[6] or "unknown",
        "population_exposed": r[7] or 0,
    } for r in rows]

import services_missions

class MissionStatusPayload(BaseModel):
    status: str

@app.patch("/api/missions/{mission_id}/status")
def update_mission_status(mission_id: str, payload: MissionStatusPayload, db: Session = Depends(get_db)):
    res = services_missions.update_mission_status(db, mission_id, payload.status)
    if "error" in res:
        raise HTTPException(status_code=res.get("code", 400), detail=res["error"])
    return res

@app.get("/api/resources/{resource_id}")
def get_resource(resource_id: str, db: Session = Depends(get_db)):
    from models import ResourceItem
    res = db.query(ResourceItem).filter(ResourceItem.id == resource_id).first()
    if not res: raise HTTPException(status_code=404, detail="Not found")
    return {"id": str(res.id), "resource_type": res.resource_type, "quantity": res.quantity, "status": res.status}

class ResourceUpdatePayload(BaseModel):
    quantity: float
    status: Optional[str] = None

@app.put("/api/resources/{resource_id}")
def update_resource(resource_id: str, payload: ResourceUpdatePayload, db: Session = Depends(get_db)):
    from models import ResourceItem
    res = db.query(ResourceItem).filter(ResourceItem.id == resource_id).first()
    if not res: raise HTTPException(status_code=404, detail="Not found")
    res.quantity = payload.quantity
    # Auto-derive status from quantity if not explicitly provided
    if payload.status:
        res.status = payload.status
    elif payload.quantity <= 0:
        res.status = "depleted"
    else:
        res.status = "available"
    db.commit()
    db.refresh(res)
    return {"id": str(res.id), "quantity": res.quantity, "status": res.status}

@app.delete("/api/resources/{resource_id}", status_code=204)
def delete_resource(resource_id: str, db: Session = Depends(get_db)):
    from models import ResourceItem
    from sqlalchemy.exc import IntegrityError
    res = db.query(ResourceItem).filter(ResourceItem.id == resource_id).first()
    if not res:
        raise HTTPException(status_code=404, detail="Depot not found.")
    try:
        db.delete(res)
        db.commit()
    except IntegrityError:
        db.rollback()
        # Count what references this depot so we can explain clearly
        ap_count = db.execute(
            text("SELECT count(*) FROM allocation_plans WHERE source_depot_id = :id"),
            {"id": resource_id}
        ).scalar() or 0
        route_count = db.execute(
            text("SELECT count(*) FROM routes WHERE depot_id = :id"),
            {"id": resource_id}
        ).scalar() or 0
        parts = []
        if ap_count:
            parts.append(f"{ap_count} allocation plan record(s)")
        if route_count:
            parts.append(f"{route_count} route record(s)")
        ref_str = " and ".join(parts) if parts else "existing records"
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot delete '{res.depot_name}': it is still referenced by {ref_str} in the database. "
                f"Edit the quantity to 0 instead — the depot will automatically be marked as Depleted."
            )
        )
    return None

class PriorityOverridePayload(BaseModel):
    priority_override: str

@app.patch("/api/zones/{zone_id}/priority-override")
def override_zone_priority(zone_id: str, payload: PriorityOverridePayload, db: Session = Depends(get_db)):
    from models import GridCell, PriorityEnum
    zone = db.query(GridCell).filter(GridCell.id == zone_id).first()
    if not zone: raise HTTPException(status_code=404, detail="Zone not found")
    try:
        new_prio = PriorityEnum(payload.priority_override.lower())
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid priority enum")
    
    zone.priority_override = new_prio
    db.commit()
    db.refresh(zone)
    return {"id": str(zone.id), "priority_override": zone.priority_override.name}

class BatchPlanPayload(BaseModel):
    zone_ids: list[str]
    create_missions: bool = True

@app.post("/api/relief-plan/generate-batch")
def generate_unified_plan_batch(payload: BatchPlanPayload, db: Session = Depends(get_db)):
    import services_logistics_batch
    res = services_logistics_batch.generate_unified_plan_batch(db, payload.zone_ids, payload.create_missions)
    if "error" in res: raise HTTPException(status_code=400, detail=res["error"])
    return res

@app.get("/api/analytics/zone-priority-ranking")
def get_zone_priority_ranking(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT
            gc.id,
            gc.severity_score,
            gc.priority::TEXT,
            gc.priority_override::TEXT,
            de.alert_level::TEXT,
            de.event_type::TEXT
        FROM grid_cells gc
        LEFT JOIN disaster_events de ON gc.related_event_id = de.id
        ORDER BY gc.severity_score DESC NULLS LAST
    """)).fetchall()
    result = []
    for r in rows:
        zone_id    = str(r[0])
        severity   = r[1]
        priority   = r[2]
        override   = r[3]
        alert_level = r[4] or "green"
        event_type  = r[5] or "unknown"
        # ASCII only label - avoid Windows encoding corruption
        sev_int = int(severity) if severity else 0
        label = f"{event_type.replace('_',' ').title()} - {alert_level.upper()} (Sev: {sev_int})"
        result.append({
            "zone_id": zone_id,
            "severity": severity,
            "priority": priority,
            "priority_override": override,
            "event_type": event_type,
            "alert_level": alert_level,
            "label": label,
        })
    return result

@app.get("/api/analytics/delivery-performance")
def get_delivery_performance(db: Session = Depends(get_db)):
    """
    Delivery performance across ALL missions and ALL incidents ever dispatched.
    Measures total response time from mission creation (allocation decision)
    to delivery — this is the true end-to-end logistics KPI.
    """
    rows = db.execute(text("""
        SELECT
            EXTRACT(EPOCH FROM (m.delivered_at - m.created_at))/60.0   AS total_minutes,
            EXTRACT(EPOCH FROM (m.delivered_at - m.dispatched_at))/60.0 AS transit_minutes,
            de.event_type::TEXT,
            de.alert_level::TEXT,
            m.team_name
        FROM missions m
        LEFT JOIN grid_cells gc ON m.zone_id = gc.id
        LEFT JOIN disaster_events de ON gc.related_event_id = de.id
        WHERE m.status = 'delivered'
          AND m.delivered_at IS NOT NULL
          AND m.created_at IS NOT NULL
        ORDER BY m.delivered_at DESC
    """)).fetchall()

    if not rows:
        return {
            "average_delivery_minutes": None,
            "average_transit_minutes": None,
            "delivered_count": 0,
            "scope": "All missions across all incidents",
            "breakdown": []
        }

    total_mins   = [float(r[0]) for r in rows if r[0] is not None]
    transit_mins = [float(r[1]) for r in rows if r[1] is not None]

    avg_total   = round(sum(total_mins) / len(total_mins), 1) if total_mins else None
    avg_transit = round(sum(transit_mins) / len(transit_mins), 1) if transit_mins else None

    breakdown = [
        {
            "team": r[4],
            "event_type": r[2] or "unknown",
            "alert_level": r[3] or "unknown",
            "total_minutes": round(float(r[0]), 1) if r[0] else None,
            "transit_minutes": round(float(r[1]), 1) if r[1] else None,
        }
        for r in rows
    ]

    return {
        "average_delivery_minutes": avg_total,
        "average_transit_minutes": avg_transit,
        "delivered_count": len(rows),
        "scope": "All missions across all incidents (from allocation decision to delivery)",
        "breakdown": breakdown,
    }

@app.get("/api/analytics/underserved-zones")
def get_underserved_zones(db: Session = Depends(get_db)):
    threshold = 50.0
    rows = db.execute(text("""
        SELECT zone_id, resource_type, coverage_percent 
        FROM allocation_plans 
        WHERE coverage_percent < :thresh 
        ORDER BY coverage_percent ASC
    """), {"thresh": threshold}).fetchall()
    return [{"zone_id": str(r[0]), "resource": r[1], "coverage_percent": r[2]} for r in rows]

@app.get("/api/analytics/missions-report")
def get_missions_report(db: Session = Depends(get_db)):
    """Full missions report: all missions with event context, supplies, status."""
    rows = db.execute(text("""
        SELECT
            m.id,
            m.status::TEXT,
            m.team_name,
            m.vehicle_id,
            m.priority::TEXT,
            m.supplies,
            m.created_at,
            m.dispatched_at,
            m.delivered_at,
            de.event_type::TEXT,
            de.alert_level::TEXT,
            gc.severity_score
        FROM missions m
        LEFT JOIN grid_cells gc ON m.zone_id = gc.id
        LEFT JOIN disaster_events de ON gc.related_event_id = de.id
        ORDER BY m.created_at DESC
    """)).fetchall()
    import json as _j
    result = []
    UNITS = {"food": "packages", "hygiene_kits": "kits", "medical": "kits", "shelter": "units"}
    for r in rows:
        supplies_raw = r[5]
        if isinstance(supplies_raw, str):
            supplies_raw = _j.loads(supplies_raw)
        supplies_raw = supplies_raw or {}
        supplies_display = []
        for k, v in supplies_raw.items():
            u = UNITS.get(k, "units")
            supplies_display.append(f"{float(v):.0f} {u} {k}")
        event_type = r[9] or "unknown"
        alert_level = r[10] or "unknown"
        label = f"{event_type.replace('_',' ').title()} - {alert_level.upper()}"
        result.append({
            "id": str(r[0]),
            "status": r[1],
            "team_name": r[2],
            "vehicle_id": r[3],
            "priority": r[4],
            "supplies": supplies_raw,
            "supplies_display": ", ".join(supplies_display) if supplies_display else "No supplies",
            "created_at": r[6].isoformat() if r[6] else None,
            "dispatched_at": r[7].isoformat() if r[7] else None,
            "delivered_at": r[8].isoformat() if r[8] else None,
            "event_type": event_type,
            "alert_level": alert_level,
            "severity": r[11],
            "incident_label": label,
        })
    return result

from fastapi.responses import Response

@app.get("/api/analytics/export")
def export_analytics(db: Session = Depends(get_db)):
    """Export a comprehensive PDF report of the entire operation."""
    summary = get_dashboard_summary(db)
    breakdown = incident_breakdown(db)
    perf = get_delivery_performance(db)
    missions = get_missions_report(db)
    zones = get_zone_priority_ranking(db)

    try:
        from io import BytesIO
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        styles = getSampleStyleSheet()
        elements = []
        
        # Title
        elements.append(Paragraph("DISASTER BRIDGE - OPERATION REPORT", styles['Title']))
        elements.append(Paragraph(f"Generated: {__import__('datetime').datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # Summary Table
        elements.append(Paragraph("=== SUMMARY ===", styles['Heading2']))
        summary_data = [
            ["Metric", "Value"],
            ["Active Incidents", str(summary['active_incidents'])],
            ["Resources Deployed (units)", str(summary['resources_deployed'])],
            ["Active Missions", str(summary['active_missions'])],
            ["Population at Risk", str(summary['population_at_risk'])],
            ["Missions Delivered", str(perf['delivered_count'])]
        ]
        if perf['average_delivery_minutes'] is not None:
            summary_data.append(["Avg Delivery Time (min)", str(perf['average_delivery_minutes'])])
            
        t_summary = Table(summary_data, colWidths=[200, 150])
        t_summary.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.beige),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        elements.append(t_summary)
        elements.append(Spacer(1, 20))
        
        # Incident Breakdown
        elements.append(Paragraph("=== INCIDENT BREAKDOWN BY ALERT LEVEL ===", styles['Heading2']))
        breakdown_data = [["Alert Level", "Count"]]
        for level, cnt in breakdown.get("by_level", {}).items():
            breakdown_data.append([str(level).upper(), str(cnt)])
            
        if len(breakdown_data) > 1:
            t_breakdown = Table(breakdown_data, colWidths=[200, 150])
            t_breakdown.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ]))
            elements.append(t_breakdown)
        else:
            elements.append(Paragraph("No active incidents to display.", styles['Normal']))
            
        elements.append(Spacer(1, 20))
        
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()
        
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=DisasterBridge_Report.pdf"}
        )
    except Exception as e:
        print("PDF Error:", e)
        return Response(content="Error generating PDF", status_code=500)


@app.get("/api/predictions/{zone_id}/history")
def get_prediction_history(zone_id: str, db: Session = Depends(get_db)):
    from models import PredictionRecord
    records = db.query(PredictionRecord).filter(PredictionRecord.zone_id == zone_id).order_by(PredictionRecord.prediction_time.desc()).all()
    return [{
        "id": str(r.id),
        "prediction_time": r.prediction_time.isoformat(),
        "model_version": r.model_version,
        "severity_score_used": r.severity_score_used,
        "predicted_demand_food": r.predicted_demand_food,
        "predicted_demand_hygiene_kits": r.predicted_demand_hygiene_kits,
        "predicted_demand_medical": r.predicted_demand_medical,
        "predicted_demand_shelter": r.predicted_demand_shelter,
        "confidence_intervals": r.confidence_intervals
    } for r in records]

@app.get("/api/zones/list")
def list_zones(db: Session = Depends(get_db)):
    """
    Returns all classified grid_cells, enriched with their related disaster_event
    so the frontend can show a human-readable label instead of a raw UUID.
    """
    rows = db.execute(text("""
        SELECT
            gc.id,
            gc.severity_score,
            CAST(gc.priority AS TEXT)        AS priority,
            CAST(de.alert_level AS TEXT)     AS alert_level,
            CAST(de.event_type AS TEXT)      AS event_type,
            de.id                            AS event_id
        FROM grid_cells gc
        JOIN disaster_events de ON gc.related_event_id = de.id
        ORDER BY gc.severity_score DESC NULLS LAST
    """)).fetchall()

    result = []
    for r in rows:
        # Build a readable label: "Earthquake – Red (Severity: 35)"
        event_type_label = (r[4] or "Event").replace("_", " ").title()
        alert_label      = (r[3] or "").upper()
        severity         = round(r[1] or 0, 1)
        label = f"{event_type_label} — {alert_label} (Severity: {severity})"

        result.append({
            "id":         str(r[0]),
            "severity":   severity,
            "priority":   r[2],
            "alert_level": r[3],
            "event_type": r[4],
            "event_id":   str(r[5]),
            "label":      label,
        })
    return result

@app.get("/api/resources")
def list_all_resources(db: Session = Depends(get_db)):
    from models import ResourceItem
    res = db.query(ResourceItem).all()
    return [{
        "id": str(r.id),
        "resource_type": r.resource_type.name if hasattr(r.resource_type, 'name') else r.resource_type,
        "quantity": r.quantity,
        "unit": r.unit,
        "status": r.status,
        "depot_name": r.depot_name,
        "lat": db.execute(text("SELECT ST_Y(location::geometry) FROM resource_items WHERE id = :id"), {"id": r.id}).scalar(),
        "lng": db.execute(text("SELECT ST_X(location::geometry) FROM resource_items WHERE id = :id"), {"id": r.id}).scalar()
    } for r in res]

@app.get("/api/analytics/incident-breakdown")
def incident_breakdown(db: Session = Depends(get_db)):
    rows = db.execute(text(
        "SELECT alert_level, count(*) as cnt FROM disaster_events GROUP BY alert_level ORDER BY cnt DESC"
    )).fetchall()
    total = db.execute(text("SELECT count(*) FROM disaster_events")).scalar()
    return {
        "total": int(total),
        "by_level": {r[0]: int(r[1]) for r in rows}
    }

@app.get("/api/analytics/coverage-summary")
def coverage_summary(db: Session = Depends(get_db)):
    """
    Real system-wide coverage:
    - zones_with_missions  = distinct grid zones that have at least 1 active mission
    - total_zones          = all classified grid zones (those linked to a disaster event)
    - coverage_pct         = zones_with_missions / total_zones * 100
    - total_events         = all disaster_events in DB
    - unserved_events      = events whose zone has NO mission yet
    - avg_alloc_coverage   = average coverage_percent from allocation_plans (resource fill %)
    """
    row = db.execute(text("""
        SELECT
            -- How many zones have at least 1 mission dispatched
            COUNT(DISTINCT m.zone_id)                              AS zones_with_missions,

            -- Total classified zones (zones linked to a real event)
            (SELECT COUNT(*) FROM grid_cells
             WHERE related_event_id IS NOT NULL)                   AS total_zones,

            -- Total disaster events
            (SELECT COUNT(*) FROM disaster_events)                 AS total_events,

            -- Events whose zone has no mission
            (SELECT COUNT(*) FROM disaster_events de
             LEFT JOIN grid_cells gc ON gc.related_event_id = de.id
             LEFT JOIN missions m2 ON m2.zone_id = gc.id
             WHERE m2.id IS NULL)                                  AS unserved_events,

            -- Average resource fill % from allocation plans (ALL time)
            (SELECT ROUND(AVG(coverage_percent)::NUMERIC, 1)
             FROM allocation_plans)                                AS avg_alloc_coverage

        FROM missions m
        WHERE m.status NOT IN ('cancelled')
    """)).fetchone()

    zones_with_missions = int(row[0]) if row[0] else 0
    total_zones         = int(row[1]) if row[1] else 0
    total_events        = int(row[2]) if row[2] else 0
    unserved_events     = int(row[3]) if row[3] else 0
    avg_alloc           = float(row[4]) if row[4] else 0.0

    coverage_pct = round((zones_with_missions / total_zones * 100), 1) if total_zones > 0 else 0.0

    return {
        "coverage_pct":        coverage_pct,        # % of classified zones with a mission
        "zones_with_missions": zones_with_missions,  # how many zones dispatched
        "total_zones":         total_zones,          # total classified zones
        "total_events":        total_events,         # all events in DB
        "unserved_events":     unserved_events,      # events with NO mission yet
        "avg_alloc_coverage":  avg_alloc,            # avg resource fill % per zone served
        # Legacy keys kept for compatibility
        "average_coverage":    coverage_pct,
        "zone_count":          zones_with_missions,
    }


@app.get("/api/analytics/zones-status")
def zones_status(db: Session = Depends(get_db)):
    """List every classified zone with its event name, alert level, and whether a mission has been dispatched."""
    rows = db.execute(text("""
        SELECT
            gc.id::TEXT,
            gc.priority::TEXT,
            gc.severity_score,
            de.raw_payload->>'title'  AS event_title,
            de.alert_level::TEXT,
            de.event_type::TEXT,
            ST_X(ST_Centroid(gc.cell_geometry::geometry)) AS lng,
            ST_Y(ST_Centroid(gc.cell_geometry::geometry)) AS lat,
            EXISTS(SELECT 1 FROM missions m WHERE m.zone_id = gc.id) AS served
        FROM grid_cells gc
        LEFT JOIN disaster_events de ON gc.related_event_id = de.id
        WHERE gc.related_event_id IS NOT NULL
        ORDER BY gc.severity_score DESC NULLS LAST
    """)).fetchall()
    return [{
        "zone_id":     r[0],
        "priority":    r[1],
        "severity":    float(r[2]) if r[2] else 0,
        "event_title": r[3] or "Unknown Event",
        "alert_level": r[4] or "green",
        "event_type":  r[5] or "unknown",
        "lng":         float(r[6]) if r[6] else 0,
        "lat":         float(r[7]) if r[7] else 0,
        "served":      bool(r[8]),
    } for r in rows]


# ── Volunteers ─────────────────────────────────────────────────────────────────

class VolunteerCreate(BaseModel):
    full_name: str
    email: str
    phone: Optional[str] = None
    role: str = "general"
    skills: Optional[list] = []
    notes: Optional[str] = None

class VolunteerStatusUpdate(BaseModel):
    status: str  # available | deployed | off_duty

@app.get("/api/volunteers")
def list_volunteers(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT v.id, v.full_name, v.email, v.phone, v.role, v.skills,
               v.status, v.notes, v.created_at,
               v.zone_id::TEXT,
               de.event_type::TEXT as assigned_event_type,
               de.alert_level::TEXT as assigned_alert_level
        FROM volunteers v
        LEFT JOIN grid_cells gc ON v.zone_id = gc.id
        LEFT JOIN disaster_events de ON gc.related_event_id = de.id
        ORDER BY v.created_at DESC
    """)).fetchall()
    result = []
    for r in rows:
        assigned_label = None
        if r[10]:
            assigned_label = f"{r[10].replace('_',' ').title()} — {(r[11] or 'green').upper()}"
        result.append({
            "id": str(r[0]),
            "full_name": r[1],
            "email": r[2],
            "phone": r[3],
            "role": r[4],
            "skills": list(r[5]) if r[5] else [],
            "status": r[6],
            "notes": r[7],
            "created_at": r[8].isoformat() if r[8] else None,
            "zone_id": r[9],
            "assigned_label": assigned_label,
        })
    return result

@app.post("/api/volunteers", status_code=201)
def create_volunteer(payload: VolunteerCreate, db: Session = Depends(get_db)):
    # Check duplicate email
    existing = db.execute(text("SELECT id FROM volunteers WHERE email=:e"), {"e": payload.email}).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="A volunteer with this email already exists")
    skills_pg = "{" + ",".join(payload.skills or []) + "}"
    row = db.execute(text("""
        INSERT INTO volunteers (full_name, email, phone, role, skills, notes)
        VALUES (:name, :email, :phone, :role, :skills, :notes)
        RETURNING id, full_name, email, role, status
    """), {
        "name": payload.full_name, "email": payload.email,
        "phone": payload.phone, "role": payload.role,
        "skills": skills_pg, "notes": payload.notes,
    }).fetchone()
    db.execute(text("COMMIT"))
    return {"id": str(row[0]), "full_name": row[1], "email": row[2], "role": row[3], "status": row[4]}

@app.patch("/api/volunteers/{volunteer_id}/status")
def update_volunteer_status(volunteer_id: str, payload: VolunteerStatusUpdate, db: Session = Depends(get_db)):
    allowed = {"available", "deployed", "off_duty"}
    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail=f"Status must be one of {allowed}")
    db.execute(text(
        "UPDATE volunteers SET status=:s WHERE id=:id"
    ), {"s": payload.status, "id": volunteer_id})
    db.execute(text("COMMIT"))
    return {"id": volunteer_id, "status": payload.status}

@app.delete("/api/volunteers/{volunteer_id}", status_code=204)
def delete_volunteer(volunteer_id: str, db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM volunteers WHERE id=:id"), {"id": volunteer_id})
    db.execute(text("COMMIT"))
    return None

@app.get("/api/volunteers/summary")
def volunteer_summary(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT status, COUNT(*) FROM volunteers GROUP BY status
    """)).fetchall()
    summary = {r[0]: int(r[1]) for r in rows}
    total = sum(summary.values())
    return {"total": total, "by_status": summary}

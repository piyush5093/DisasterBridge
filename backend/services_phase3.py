from sqlalchemy.orm import Session
from sqlalchemy import text
from models import ResourceItem, ResourceTypeEnum, ResourceStatusEnum, DisasterEvent, GridCell, PriorityEnum, AlertLevelEnum

def create_resource(db: Session, payload: dict):
    res = ResourceItem(
        resource_type=ResourceTypeEnum(payload['resource_type']),
        quantity=payload['quantity'],
        unit=payload['unit'],
        location=f"SRID=4326;POINT({payload['lng']} {payload['lat']})",
        depot_name=payload['depot_name'],
        status=ResourceStatusEnum(payload.get('status', 'available'))
    )
    db.add(res)
    db.commit()
    db.refresh(res)
    return {"id": str(res.id), "status": "created"}

def get_resources_near(db: Session, lat: float, lng: float, radius_km: float):
    radius_meters = radius_km * 1000
    query = text('''
        SELECT id, resource_type, quantity, unit, depot_name, status,
               ST_X(location::geometry) as lng, ST_Y(location::geometry) as lat
        FROM resource_items
        WHERE ST_DWithin(location::geography, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, :radius)
    ''')
    rows = db.execute(query, {"lng": lng, "lat": lat, "radius": radius_meters}).fetchall()
    
    return [
        {
            "id": str(r.id), "resource_type": r.resource_type,
            "quantity": r.quantity, "unit": r.unit, "depot_name": r.depot_name,
            "status": r.status, "lat": r.lat, "lng": r.lng
        } for r in rows
    ]

def classify_zones(db: Session, event_id: str):
    event = db.query(DisasterEvent).filter(DisasterEvent.id == event_id).first()
    if not event:
        return {"error": "Event not found"}

    # Auto-compute impact_extent if missing — 50km buffer around the event location.
    # This removes the hard dependency on a prior manual compute-impact-extent call.
    if event.impact_extent is None:
        db.execute(text("""
            UPDATE disaster_events
            SET impact_extent = ST_Buffer(location::geography, 50000)::geometry
            WHERE id = :id
        """), {"id": event_id})
        db.commit()
        db.refresh(event)

    # Severity calculation: 0.4*pop + 0.3*alert + 0.2*buildings + 0.1*scarcity
    pop = event.population_exposed or 0
    buildings = event.buildings_affected or 0

    # Normalize population (100k is max for a local cell)
    norm_pop = min(100.0, (pop / 100000.0) * 100)

    # Normalize alert level
    alert_scores = {AlertLevelEnum.red: 100, AlertLevelEnum.orange: 70, AlertLevelEnum.green: 30,
                    AlertLevelEnum.critical: 100, AlertLevelEnum.high: 70, AlertLevelEnum.medium: 50, AlertLevelEnum.low: 30}
    norm_alert = alert_scores.get(event.alert_level, 50)

    # Normalize buildings (10k max)
    norm_buildings = min(100.0, (buildings / 10000.0) * 100)

    # Resource scarcity (50% baseline)
    norm_scarcity = 50.0

    severity = (0.4 * norm_pop) + (0.3 * norm_alert) + (0.2 * norm_buildings) + (0.1 * norm_scarcity)

    # Priority calibration — thresholds derived from real severity distribution analysis:
    #
    # With this dataset, population_exposed and buildings_affected are NULL for ~99% of events,
    # so the severity formula collapses to: 0.3*alert_score + 0.1*50 (scarcity baseline).
    # This produces a structural ceiling per alert level:
    #   green  → alert_score=30  → max severity = 0.3*30 + 5 = 14
    #   low    → alert_score=30  → max severity = 14
    #   orange → alert_score=70  → max severity = 0.3*70 + 5 = 26
    #   red    → alert_score=100 → max severity = 0.3*100 + 5 = 35
    # When population/building data IS present (1 in 495 events), severity can reach 99.
    #
    # Observed distribution across 7 classified zones:
    #   MIN=14, MAX=99, AVG=52.6, MEDIAN=35
    #   p33=25.8, p67=90.0
    #
    # Recalibrated thresholds (percentile-informed, alert-level-aligned):
    #   HIGH   : severity >= 60  (requires orange/red + some population data OR red alert alone in future)
    #   MEDIUM : severity >= 22  (orange alert and above, even without population data)
    #   LOW    : severity < 22   (green/low-alert events with no additional data)
    if severity >= 60: priority = PriorityEnum.high
    elif severity >= 22: priority = PriorityEnum.medium
    else: priority = PriorityEnum.low

    # Extract EWKT of the (now-guaranteed) impact extent
    geom_ewkt = db.execute(
        text("SELECT ST_AsEWKT(impact_extent) FROM disaster_events WHERE id = :id"),
        {"id": event_id}
    ).fetchone()[0]

    query = text('''
        INSERT INTO grid_cells (id, cell_geometry, related_event_id, severity_score, population_exposed, priority)
        VALUES (gen_random_uuid(), :geom, :event_id, :sev, :pop, :prio)
        RETURNING id
    ''')

    result = db.execute(query, {
        "geom": geom_ewkt, "event_id": event.id, "sev": severity,
        "pop": pop, "prio": priority.name
    }).fetchone()

    db.commit()

    return {"status": "classified", "grid_cell_id": str(result[0]), "severity_score": severity, "priority": priority.name}

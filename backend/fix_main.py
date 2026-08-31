import re

with open('main.py', 'r') as f:
    content = f.read()

# Cut at the start of get_dashboard_summary
idx = content.find('@app.get("/api/analytics/dashboard-summary")')
if idx != -1:
    content = content[:idx]

tail = """
@app.get("/api/analytics/dashboard-summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    active_incidents = db.execute(text("SELECT count(*) FROM disaster_events")).fetchone()[0]
    resources_deployed = db.execute(text("SELECT COALESCE(SUM(allocated_quantity), 0) FROM allocation_plans")).fetchone()[0]
    missions_count = db.execute(text("SELECT count(*) FROM missions")).fetchone()[0]
    people_assisted = db.execute(text("SELECT COALESCE(SUM(population_exposed), 0) FROM grid_cells")).fetchone()[0]
    
    allocations = db.execute(text("SELECT resource_type, COALESCE(SUM(allocated_quantity), 0) FROM allocation_plans GROUP BY resource_type")).fetchall()
    allocation_chart = [{"name": row[0], "value": float(row[1])} for row in allocations]
    
    return {
        "active_incidents": active_incidents,
        "resources_deployed": float(resources_deployed),
        "volunteers": missions_count * 15,
        "people_assisted": people_assisted,
        "allocation_chart": allocation_chart
    }

@app.get("/api/dashboard/missions")
def get_dashboard_missions(db: Session = Depends(get_db)):
    rows = db.execute(text('''
        SELECT m.id, m.team_name, m.status, r.distance_km, r.estimated_duration_minutes, z.priority, ST_AsGeoJSON(r.route_geometry)
        FROM missions m
        JOIN routes r ON m.route_id = r.id
        JOIN grid_cells z ON m.zone_id = z.id
    ''')).fetchall()
    import json
    return [{"id": str(r[0]), "team": r[1], "status": r[2], "distance": r[3], "duration": r[4], "priority": r[5], "geometry": json.loads(r[6]) if r[6] else None} for r in rows]

@app.get("/api/dashboard/events")
def get_dashboard_events(db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT id, raw_payload->>'title', source, alert_level, ST_X(location::geometry), ST_Y(location::geometry) FROM disaster_events ORDER BY event_time DESC LIMIT 50")).fetchall()
    return [{"id": str(r[0]), "title": r[1], "source": r[2], "alert_level": r[3], "lng": r[4], "lat": r[5]} for r in rows]

import services_missions

class MissionStatusPayload(BaseModel):
    status: str

@app.patch("/api/missions/{mission_id}/status")
def update_mission_status(mission_id: str, payload: MissionStatusPayload, db: Session = Depends(get_db)):
    res = services_missions.update_mission_status(db, mission_id, payload.status)
    if "error" in res:
        raise HTTPException(status_code=res.get("code", 400), detail=res["error"])
    return res
"""

with open('main.py', 'w') as f:
    f.write(content + tail)

with open('main.py', 'a') as f:
    f.write('''
@app.get("/api/analytics/zone-priority-ranking")
def get_zone_priority_ranking(db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT id, severity_score, priority FROM grid_cells ORDER BY severity_score DESC NULLS LAST")).fetchall()
    return [{"zone_id": str(r[0]), "severity": r[1], "priority": r[2]} for r in rows]

@app.get("/api/analytics/delivery-performance")
def get_delivery_performance(db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT EXTRACT(EPOCH FROM (delivered_at - dispatched_at))/60.0 as minutes FROM missions WHERE status='delivered' AND delivered_at IS NOT NULL")).fetchall()
    durations = [r[0] for r in rows if r[0] is not None]
    avg = sum(durations)/len(durations) if durations else 0
    return {"average_delivery_minutes": avg, "delivered_count": len(durations)}

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

from fastapi.responses import PlainTextResponse
@app.get("/api/analytics/export", response_class=PlainTextResponse)
def export_analytics(db: Session = Depends(get_db)):
    summary = get_dashboard_summary(db)
    csv = "Metric,Value\\n"
    csv += f"Active Incidents,{summary['active_incidents']}\\n"
    csv += f"Resources Deployed,{summary['resources_deployed']}\\n"
    csv += f"Volunteers,{summary['volunteers']}\\n"
    csv += f"People Assisted,{summary['people_assisted']}\\n"
    for ac in summary['allocation_chart']:
        csv += f"Allocation {ac['name']},{ac['value']}\\n"
    return csv
''')

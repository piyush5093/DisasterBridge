import sys
with open('main.py', 'a') as f:
    f.write('''
@app.get("/api/analytics/incident-breakdown")
def incident_breakdown(db: Session = Depends(get_db)):
    """Returns per-alert-level counts from disaster_events — same table as the Active Incidents KPI."""
    rows = db.execute(text(
        "SELECT alert_level, count(*) as cnt FROM disaster_events GROUP BY alert_level ORDER BY cnt DESC"
    )).fetchall()
    total = db.execute(text("SELECT count(*) FROM disaster_events")).scalar()
    return {
        "total": total,
        "by_level": {r[0]: int(r[1]) for r in rows}
    }
''')

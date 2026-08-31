with open('main.py', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# Find and remove the broken appended block, then re-add it clean
marker = '\n@app.get("/api/analytics/incident-breakdown")'
if marker in content:
    content = content[:content.index(marker)]

# Append the clean version
new_block = '''
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
'''

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content + new_block)

print("Done. Wrote clean endpoint.")

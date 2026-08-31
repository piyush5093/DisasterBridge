with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the incident-breakdown endpoint to append after it
new_endpoint = '''
@app.get("/api/analytics/coverage-summary")
def coverage_summary(db: Session = Depends(get_db)):
    """Average coverage_percent across all allocation_plans for the latest plan_run_id."""
    result = db.execute(text("""
        SELECT AVG(coverage_percent), COUNT(*), MIN(coverage_percent), MAX(coverage_percent)
        FROM allocation_plans
        WHERE plan_run_id = (SELECT plan_run_id FROM allocation_plans ORDER BY created_at DESC LIMIT 1)
    """)).fetchone()
    if result[0] is None:
        return {"average_coverage": None, "zone_count": 0, "min_coverage": None, "max_coverage": None}
    return {
        "average_coverage": round(float(result[0]), 1),
        "zone_count": int(result[1]),
        "min_coverage": round(float(result[2]), 1),
        "max_coverage": round(float(result[3]), 1)
    }
'''

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content + new_endpoint)

print("Done.")

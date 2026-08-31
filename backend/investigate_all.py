from sqlalchemy import create_engine, text
import urllib.request, json, os, glob

engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')

# ============ SECTION 1 ============
print("="*60)
print("SECTION 1 — impact_extent status")
print("="*60)
with engine.connect() as con:
    total = con.execute(text("SELECT count(*) FROM disaster_events")).scalar()
    with_ext = con.execute(text("SELECT count(*) FROM disaster_events WHERE impact_extent IS NOT NULL")).scalar()
    with_pop = con.execute(text("SELECT count(*) FROM disaster_events WHERE population_exposed IS NOT NULL")).scalar()
    with_bld = con.execute(text("SELECT count(*) FROM disaster_events WHERE buildings_affected IS NOT NULL")).scalar()
    print(f"Total events:                    {total}")
    print(f"With impact_extent:              {with_ext}")
    print(f"With population_exposed:         {with_pop}")
    print(f"With buildings_affected:         {with_bld}")

# ============ SECTION 2 ============
print("\n" + "="*60)
print("SECTION 2 — resource_items")
print("="*60)
with engine.connect() as con:
    rows = con.execute(text(
        "SELECT depot_name, CAST(resource_type AS TEXT), quantity, unit, status FROM resource_items ORDER BY depot_name, resource_type"
    )).fetchall()
    for r in rows:
        print(f"  {r[0]:<30} {r[1]:<10} qty={r[2]:>8.0f} {r[3]:<10} {r[4]}")

# Test GET /api/resources
print("\nTesting GET /api/resources ...")
try:
    with urllib.request.urlopen("http://localhost:8000/api/resources", timeout=5) as resp:
        data = json.loads(resp.read())
        print(f"  API returned {len(data)} rows")
        for r in data:
            print(f"  {r.get('depot_name','?'):<30} {r.get('resource_type','?'):<10} qty={r.get('quantity',0):>8.0f}")
except Exception as e:
    print(f"  FAILED: {e}")

# ============ SECTION 3 ============
print("\n" + "="*60)
print("SECTION 3 — ML model files")
print("="*60)
for path in ["models_v1/demand_model.pkl", "models_v2/demand_model.pkl",
             "models_v1/metrics.json", "models_v2/metrics.json"]:
    full = os.path.join("D:/Disaster/backend", path)
    if os.path.exists(full):
        sz = os.path.getsize(full)
        mtime = os.path.getmtime(full)
        import datetime
        mt = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        if path.endswith('.json'):
            with open(full) as f:
                content = f.read()
            print(f"  {path}: {sz} bytes | {mt}")
            print(f"    CONTENT: {content[:500]}")
        else:
            print(f"  {path}: {sz} bytes | {mt}")
    else:
        print(f"  {path}: NOT FOUND")

# Grid cells for prediction tests
print("\n--- Grid cells for prediction tests ---")
with engine.connect() as con:
    zones = con.execute(text("SELECT id, severity_score, priority FROM grid_cells ORDER BY severity_score DESC")).fetchall()
    for z in zones:
        print(f"  id={str(z[0])[:8]}... severity={z[1]:.1f} priority={z[2]}")

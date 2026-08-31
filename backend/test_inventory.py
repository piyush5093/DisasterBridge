import urllib.request, json
from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')

def post(path, body=None):
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(f"http://localhost:8000{path}", data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"__error__": e.code, "detail": e.read().decode()}

def get_inventory():
    with engine.connect() as con:
        rows = con.execute(text(
            "SELECT depot_name, CAST(resource_type AS TEXT), quantity, status FROM resource_items ORDER BY depot_name"
        )).fetchall()
        return {f"{r[0]}/{r[1]}": (float(r[2]), r[3]) for r in rows}

def show_inventory(label):
    inv = get_inventory()
    print(f"\n--- {label} ---")
    for k, (qty, status) in inv.items():
        print(f"  {k:<40} qty={qty:>8.1f}  status={status}")
    return inv

print("="*60)
print("REAL BEFORE/AFTER INVENTORY DEDUCTION TEST")
print("="*60)

# BEFORE
inv_before = show_inventory("BEFORE any allocation")

# Get a zone to allocate to
with engine.connect() as con:
    zone = con.execute(text("SELECT id FROM grid_cells ORDER BY severity_score DESC LIMIT 1")).fetchone()
    zone_id = str(zone[0])
print(f"\nUsing zone_id: {zone_id[:8]}...")

# ALLOCATION 1
print("\n[RUN 1] POST /api/allocation/optimize ...")
r1 = post(f"/api/allocation/optimize?zone_id={zone_id}")
print(f"  Response: {json.dumps(r1)[:400]}")

inv_after1 = show_inventory("AFTER allocation 1")

# Compare
print("\n--- Quantity changes after allocation 1 ---")
for k in inv_before:
    before_qty = inv_before[k][0]
    after_qty  = inv_after1[k][0]
    delta = after_qty - before_qty
    if abs(delta) > 0.01:
        print(f"  CHANGED: {k}  {before_qty:.1f} -> {after_qty:.1f}  (delta={delta:.1f})")
    else:
        print(f"  unchanged: {k}  {before_qty:.1f}")

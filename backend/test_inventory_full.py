import urllib.request, json, time
from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
BASE = "http://localhost:8000"

def post(path, body=None):
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"__error__": e.code, "detail": e.read().decode()}

def patch(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=data, method='PATCH')
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"__error__": e.code, "detail": e.read().decode()}

def inventory():
    with engine.connect() as con:
        rows = con.execute(text(
            "SELECT depot_name, CAST(resource_type AS TEXT), quantity, status FROM resource_items ORDER BY depot_name"
        )).fetchall()
        return {f"{r[0]}/{r[1]}": (float(r[2]), r[3]) for r in rows}

def show(label):
    inv = inventory()
    print(f"\n--- {label} ---")
    for k, (qty, st) in inv.items():
        print(f"  {k:<40} qty={qty:>8.1f}  [{st}]")
    return inv

# Get 2 different zones
with engine.connect() as con:
    zones = con.execute(text("SELECT id FROM grid_cells ORDER BY severity_score DESC LIMIT 2")).fetchall()
    zone1_id = str(zones[0][0])
    zone2_id = str(zones[1][0]) if len(zones) > 1 else zone1_id

print("="*60)
print("FULL END-TO-END INVENTORY TEST")
print("="*60)
print(f"Zone 1: {zone1_id[:8]}...")
print(f"Zone 2: {zone2_id[:8]}...")

# STEP 1: Baseline
inv0 = show("BASELINE (before any allocation)")

# STEP 2: Allocation 1 on zone 1
print(f"\n[ALLOC 1] Allocating to zone 1 ({zone1_id[:8]}...)")
r1 = post(f"/api/allocation/optimize?zone_id={zone1_id}")
if "__error__" in r1:
    print(f"  FAILED: {r1}")
else:
    allocs = r1.get("allocations", [])
    for a in allocs:
        print(f"  allocated {a['quantity']:.1f} {a['resource_type']} from depot {a['depot_id'][:8]}...")

inv1 = show("AFTER allocation 1")

print("\n--- Changes after alloc 1 ---")
for k in inv0:
    delta = inv1[k][0] - inv0[k][0]
    if abs(delta) > 0.01:
        print(f"  DEDUCTED: {k}  {inv0[k][0]:.1f} -> {inv1[k][0]:.1f}  (={delta:.1f})")

# STEP 3: Allocation 2 on zone 2 (will use reduced stock)
print(f"\n[ALLOC 2] Allocating to zone 2 ({zone2_id[:8]}...)")
r2 = post(f"/api/allocation/optimize?zone_id={zone2_id}")
if "__error__" in r2:
    print(f"  FAILED: {r2}")
else:
    allocs2 = r2.get("allocations", [])
    for a in allocs2:
        print(f"  allocated {a['quantity']:.1f} {a['resource_type']} from depot {a['depot_id'][:8]}...")

inv2 = show("AFTER allocation 2 (cumulative)")

print("\n--- Cumulative changes (baseline vs after 2 allocations) ---")
for k in inv0:
    total_delta = inv2[k][0] - inv0[k][0]
    if abs(total_delta) > 0.01:
        print(f"  TOTAL DEDUCTED: {k}  {inv0[k][0]:.1f} -> {inv2[k][0]:.1f}  (={total_delta:.1f})")

# STEP 4: Test cancellation restore
print("\n[CANCEL] Getting a mission to cancel ...")
with engine.connect() as con:
    mission_row = con.execute(text("SELECT id FROM missions LIMIT 1")).fetchone()

if mission_row:
    mission_id = str(mission_row[0])
    print(f"  Cancelling mission {mission_id[:8]}...")
    cr = patch(f"/api/missions/{mission_id}/status", {"status": "cancelled"})
    print(f"  Cancel result: status={cr.get('status')} error={cr.get('error','none')}")
    inv3 = show("AFTER cancellation (inventory should be restored)")
    print("\n--- Change after cancel ---")
    for k in inv2:
        delta = inv3[k][0] - inv2[k][0]
        if abs(delta) > 0.01:
            print(f"  RESTORED: {k}  {inv2[k][0]:.1f} -> {inv3[k][0]:.1f}  (+{delta:.1f})")
else:
    print("  No missions found to cancel (dispatch first via Logistics page)")

# STEP 5: Verify API matches DB
print("\n[VERIFY] GET /api/resources matches DB")
with urllib.request.urlopen(f"{BASE}/api/resources", timeout=5) as resp:
    api_data = json.loads(resp.read())
with engine.connect() as con:
    db_data = {r[0]: float(r[2]) for r in con.execute(text(
        "SELECT depot_name, CAST(resource_type AS TEXT), quantity FROM resource_items ORDER BY depot_name"
    )).fetchall()}

for item in api_data:
    api_qty = item['quantity']
    db_qty  = db_data.get(item['depot_name'], -1)
    match = abs(api_qty - db_qty) < 0.01
    print(f"  {item['depot_name']:<30} API={api_qty:>8.1f}  DB={db_qty:>8.1f}  MATCH={match}")

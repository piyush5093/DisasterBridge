import urllib.request, json
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

VUL = {"vulnerability_demographics": {"elderly": 0.3, "children": 0.2, "medically_dependent": 0.1}}

def predict(zone_id):
    r = post(f"/predict/demand/{zone_id}", VUL)
    if "__error__" in r:
        print(f"  ERROR: {r}")
        return None
    return r

with engine.connect() as con:
    zones = con.execute(text("SELECT id, severity_score FROM grid_cells ORDER BY severity_score DESC")).fetchall()
    zone_ids = [(str(z[0]), float(z[1])) for z in zones]

print("="*60)
print("ML VERIFICATION TESTS")
print("="*60)

high_id, high_sev = zone_ids[0]   # sev=99
low_id,  low_sev  = zone_ids[-1]  # sev=14

# T1: High severity prediction
print(f"\n[T1] HIGH severity zone (sev={high_sev}): {high_id[:8]}...")
r1 = predict(high_id)
if r1:
    print(f"  food={r1['food']['predicted']:.1f}  water={r1['water']['predicted']:.1f}  medical={r1['medical']['predicted']:.1f}  shelter={r1['shelter']['predicted']:.1f}")
    food_ci_w_high = abs(r1['food']['ci_upper'] - r1['food']['ci_lower'])
    print(f"  food CI=[{r1['food']['ci_lower']:.1f}, {r1['food']['ci_upper']:.1f}] width={food_ci_w_high:.1f}")

# T2: Low severity prediction
print(f"\n[T2] LOW severity zone (sev={low_sev}): {low_id[:8]}...")
r2 = predict(low_id)
if r2:
    print(f"  food={r2['food']['predicted']:.1f}  water={r2['water']['predicted']:.1f}  medical={r2['medical']['predicted']:.1f}  shelter={r2['shelter']['predicted']:.1f}")
    food_ci_w_low = abs(r2['food']['ci_upper'] - r2['food']['ci_lower'])
    print(f"  food CI=[{r2['food']['ci_lower']:.1f}, {r2['food']['ci_upper']:.1f}] width={food_ci_w_low:.1f}")

if r1 and r2:
    diff = abs(r1['food']['predicted'] - r2['food']['predicted'])
    print(f"\n  Food demand DIFF (sev=99 vs sev=14): {diff:.1f}")
    print(f"  Input-dependent: {diff > 1.0}")

# T3: Mutate DB severity, re-predict
print(f"\n[T3] Mutate severity {high_sev}->10.0, re-predict same zone")
with engine.connect() as con:
    con.execute(text("UPDATE grid_cells SET severity_score=10.0 WHERE id=:id"), {"id": high_id})
    con.commit()
r3 = predict(high_id)
with engine.connect() as con:
    con.execute(text("UPDATE grid_cells SET severity_score=99.0 WHERE id=:id"), {"id": high_id})
    con.commit()
if r1 and r3:
    print(f"  sev=99 → food={r1['food']['predicted']:.1f}")
    print(f"  sev=10 → food={r3['food']['predicted']:.1f}")
    print(f"  Model responds to severity change: {abs(r1['food']['predicted'] - r3['food']['predicted']) > 0.1}")

# T4: CI widths across 3 zones
print(f"\n[T4] CI band widths across 3 zones")
widths = []
for zid, zsev in zone_ids[:3]:
    rz = predict(zid)
    if rz:
        w = abs(rz['food']['ci_upper'] - rz['food']['ci_lower'])
        widths.append(round(w, 1))
        print(f"  sev={zsev:.0f}  food CI width={w:.1f}")
all_same = len(set(widths)) == 1
print(f"  All CI widths identical: {all_same} → {'HARDCODED' if all_same else 'REAL — varies'}")

# T5: Simulation is non-destructive
print(f"\n[T5] Simulation non-destructive")
with engine.connect() as con:
    before = con.execute(text("SELECT count(*) FROM prediction_records")).scalar()
sim_r = post("/api/predictions/simulate", {"zone_id": high_id, "severity_delta": 20.0})
with engine.connect() as con:
    after = con.execute(text("SELECT count(*) FROM prediction_records")).scalar()
print(f"  prediction_records before: {before}, after: {after}")
print(f"  Non-destructive: {before == after}")
print(f"  Sim response keys: {list(sim_r.keys()) if isinstance(sim_r, dict) else sim_r}")
if "__error__" not in sim_r:
    food_sim = sim_r.get('food', {}).get('predicted') if isinstance(sim_r.get('food'), dict) else sim_r.get('food')
    print(f"  Sim food value (preview only): {food_sim}")

# T6: Recalibrate — confirm values change
print(f"\n[T6] Recalibrate")
mid_id = zone_ids[2][0]
mid_sev = zone_ids[2][1]
r_pre = predict(mid_id)
r_recal = post(f"/api/predictions/{mid_id}/recalibrate", {"new_severity": 90.0, "reason": "Field report verification test"})
print(f"  Zone sev={mid_sev}")
if r_pre:
    print(f"  Pre-recal  food={r_pre['food']['predicted']:.1f}")
print(f"  Recal response: {json.dumps(r_recal)[:400]}")

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

DEFAULT_VUL = {"vulnerability_demographics": {"elderly": 0.3, "children": 0.2, "medically_dependent": 0.1}}

with engine.connect() as con:
    zones = con.execute(text("SELECT id, severity_score FROM grid_cells ORDER BY severity_score DESC")).fetchall()
    zone_ids = [(str(z[0]), float(z[1])) for z in zones]

high_id, high_sev = zone_ids[0]
low_id,  low_sev  = zone_ids[-1]

# First see the raw response to understand key names
print("[DEBUG] Raw response from /predict/demand:")
r_test = post(f"/predict/demand/{high_id}", DEFAULT_VUL)
print(json.dumps(r_test, indent=2)[:600])

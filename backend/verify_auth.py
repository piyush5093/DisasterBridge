import urllib.request, json

BASE = "http://localhost:8000"

def post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

def get(path, token=None):
    req = urllib.request.Request(f"{BASE}{path}")
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

print("=" * 55)
print("AUTH ENDPOINT VERIFICATION")
print("=" * 55)

# Test 1: Login with correct credentials (all 3 commanders)
accounts = [
    ("kamin@disasterbridge.com",  "commander123"),
    ("sharma@disasterbridge.com", "fieldops456"),
    ("admin@disasterbridge.com",  "admin789"),
]
tokens = {}
for email, pw in accounts:
    code, res = post("/api/auth/login", {"email": email, "password": pw})
    ok = code == 200 and "access_token" in res
    token = res.get("access_token","")
    name  = res.get("commander",{}).get("full_name","?")
    role  = res.get("commander",{}).get("role","?")
    print(f"\n[LOGIN] {email}")
    print(f"  HTTP {code} | name={name} | role={role}")
    print(f"  Token: {token[:30]}... | PASS={ok}")
    tokens[email] = token

# Test 2: Wrong password -> 401
code, res = post("/api/auth/login", {"email": "kamin@disasterbridge.com", "password": "wrongpassword"})
print(f"\n[WRONG PASSWORD] HTTP {code} | detail={res.get('detail')} | PASS={code==401}")

# Test 3: GET /api/auth/me with valid token
code, res = get("/api/auth/me", tokens.get("kamin@disasterbridge.com"))
print(f"\n[GET /me] HTTP {code} | full_name={res.get('full_name')} | email={res.get('email')} | PASS={code==200}")

# Test 4: GET /api/auth/me with NO token -> 401
code, res = get("/api/auth/me")
print(f"\n[GET /me no token] HTTP {code} | detail={res.get('detail')} | PASS={code==401}")

# Test 5: Logout
code, res = post("/api/auth/logout", {})
print(f"\n[LOGOUT] HTTP {code} | ok={res.get('ok')} | PASS={code==200}")

# Test 6: Confirm commanders table in DB
from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
with engine.connect() as con:
    rows = con.execute(text("SELECT full_name, email, role FROM commanders ORDER BY created_at")).fetchall()
    print(f"\n[DB] commanders table: {len(rows)} rows")
    for r in rows:
        print(f"  name={r[0]:<30} email={r[1]:<35} role={r[2]}")

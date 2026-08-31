import urllib.request, json

BASE = "http://localhost:8000"

def req(method, path, body=None, token=None):
    data = json.dumps(body).encode() if body else b""
    r = urllib.request.Request(f"{BASE}{path}", data=data if data else None, method=method)
    if data: r.add_header('Content-Type', 'application/json')
    if token: r.add_header('Authorization', f'Bearer {token}')
    try:
        with urllib.request.urlopen(r, timeout=10) as res:
            return res.status, json.loads(res.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

# Get admin token
_, login = req("POST", "/api/auth/login", {"email": "kamin@disasterbridge.com", "password": "commander123"})
admin_token = login["access_token"]
print(f"Admin token: {admin_token[:30]}...")

# Get non-admin token
_, login2 = req("POST", "/api/auth/login", {"email": "sharma@disasterbridge.com", "password": "fieldops456"})
user_token = login2["access_token"]

print("\n=== TEST 1: List commanders (admin) ===")
code, res = req("GET", "/api/commanders", token=admin_token)
print(f"HTTP {code} | count={len(res)} | PASS={code==200}")
for c in res:
    print(f"  {c['full_name']:<30} {c['email']:<38} role={c['role']} active={c['is_active']}")

print("\n=== TEST 2: List commanders (non-admin → 403) ===")
code, res = req("GET", "/api/commanders", token=user_token)
print(f"HTTP {code} | detail={res.get('detail')} | PASS={code==403}")

print("\n=== TEST 3: Create new commander (admin) ===")
code, res = req("POST", "/api/commanders", {
    "full_name": "Commander Singh",
    "email": "singh@disasterbridge.com",
    "password": "testpass123",
    "role": "commander"
}, token=admin_token)
new_id = res.get("id", "")
print(f"HTTP {code} | id={new_id[:8]}... | name={res.get('full_name')} | PASS={code==200}")

print("\n=== TEST 4: Duplicate email → 409 ===")
code, res = req("POST", "/api/commanders", {
    "full_name": "Duplicate",
    "email": "singh@disasterbridge.com",
    "password": "doesntmatter",
    "role": "commander"
}, token=admin_token)
print(f"HTTP {code} | detail={res.get('detail')} | PASS={code==409}")

print("\n=== TEST 5: New commander can log in ===")
code, res = req("POST", "/api/auth/login", {"email": "singh@disasterbridge.com", "password": "testpass123"})
print(f"HTTP {code} | name={res.get('commander',{}).get('full_name')} | PASS={code==200}")

print("\n=== TEST 6: Deactivate commander ===")
code, res = req("DELETE", f"/api/commanders/{new_id}", token=admin_token)
print(f"HTTP {code} | ok={res.get('ok')} | PASS={code==200}")

print("\n=== TEST 7: Deactivated commander cannot log in → 401 ===")
code, res = req("POST", "/api/auth/login", {"email": "singh@disasterbridge.com", "password": "testpass123"})
print(f"HTTP {code} | detail={res.get('detail')} | PASS={code==401}")

print("\n=== TEST 8: Reactivate commander ===")
code, res = req("PATCH", f"/api/commanders/{new_id}/reactivate", token=admin_token)
print(f"HTTP {code} | ok={res.get('ok')} | PASS={code==200}")

print("\n=== TEST 9: Reactivated commander can log in again ===")
code, res = req("POST", "/api/auth/login", {"email": "singh@disasterbridge.com", "password": "testpass123"})
print(f"HTTP {code} | name={res.get('commander',{}).get('full_name')} | PASS={code==200}")

print("\n=== TEST 10: Admin cannot deactivate themselves → 400 ===")
_, me = req("GET", "/api/auth/me", token=admin_token)
code, res = req("DELETE", f"/api/commanders/{me['id']}", token=admin_token)
print(f"HTTP {code} | detail={res.get('detail')} | PASS={code==400}")

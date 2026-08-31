"""
Fix inventory: can't delete duplicate rows due to FK constraint from allocation_plans.
Instead, zero out the duplicates and set the canonical rows to seed values.
"""
from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')

with engine.connect() as con:
    print("=== Current inventory ===")
    rows = con.execute(text("SELECT id, resource_type::TEXT, quantity FROM resource_items ORDER BY resource_type, quantity DESC")).fetchall()
    for r in rows:
        print(f"  {r[0]} | {r[1]:<10} | qty={r[2]:.1f}")

    # For each resource_type, keep the highest-qty row at seed value, zero the rest
    seeds = {'food': 5000.0, 'water': 8000.0, 'medical': 500.0, 'shelter': 200.0}
    for rtype, seed_qty in seeds.items():
        type_rows = [r for r in rows if r[1] == rtype]
        if not type_rows:
            continue
        # The first row (highest qty) gets the seed value
        canonical_id = type_rows[0][0]
        con.execute(text("UPDATE resource_items SET quantity=:q, status='available' WHERE id=:id"),
                    {"q": seed_qty, "id": canonical_id})
        # Any additional rows for same type get zeroed (can't delete due to FK)
        for extra in type_rows[1:]:
            con.execute(text("UPDATE resource_items SET quantity=0.0, status='depleted' WHERE id=:id"),
                        {"id": extra[0]})
    con.execute(text("COMMIT"))

    print("\n=== After fix ===")
    rows2 = con.execute(text("SELECT id, resource_type::TEXT, quantity, unit, status::TEXT FROM resource_items ORDER BY resource_type, quantity DESC")).fetchall()
    for r in rows2:
        print(f"  {r[0]} | {r[1]:<10} | qty={r[2]:.1f} {r[3]:<8} | {r[4]}")

    # Verify missions API returns proper data
    import urllib.request, json
    res = json.loads(urllib.request.urlopen("http://localhost:8000/api/dashboard/missions", timeout=10).read())
    print(f"\n=== Missions API ({len(res)} missions) ===")
    for m in res[:3]:
        print(f"  [{m['status']:>10}] {m.get('event_type','?')} / {m.get('alert_level','?')} | supplies={m['supplies']} | team={m['team']}")

    # Verify dashboard summary
    res2 = json.loads(urllib.request.urlopen("http://localhost:8000/api/analytics/dashboard-summary", timeout=10).read())
    print(f"\n=== Dashboard summary ===")
    print(f"  active_incidents: {res2['active_incidents']}")
    print(f"  resources_deployed: {res2['resources_deployed']}")
    print(f"  active_missions: {res2.get('active_missions','N/A')}")
    print(f"  population_at_risk: {res2['population_at_risk']}")
    print(f"  allocation_chart: {res2['allocation_chart']}")

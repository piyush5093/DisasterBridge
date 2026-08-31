from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
with engine.connect() as con:
    # Get missions table columns
    cols = con.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name='missions' ORDER BY ordinal_position"
    )).fetchall()
    col_names = [c[0] for c in cols]
    print('missions columns:', col_names)

    # Get sample rows
    rows = con.execute(text('SELECT * FROM missions ORDER BY created_at DESC LIMIT 3')).fetchall()
    print(f'\nTotal missions: {con.execute(text("SELECT COUNT(*) FROM missions")).scalar()}')
    for r in rows:
        d = dict(zip(col_names, r))
        print('\nMission:', d)

    # Check missions/dashboard API response
    import urllib.request, json
    res = json.loads(urllib.request.urlopen('http://localhost:8000/api/dashboard/missions', timeout=10).read())
    print('\n=== API /api/dashboard/missions sample:')
    for m in res[:2]:
        print(m)

    # Dashboard summary
    res2 = json.loads(urllib.request.urlopen('http://localhost:8000/api/analytics/dashboard-summary', timeout=10).read())
    print('\n=== Dashboard summary:')
    print(res2)

    # Check allocation plans total
    total_alloc = con.execute(text('SELECT COALESCE(SUM(quantity),0) FROM allocation_plans')).scalar()
    print(f'\nTotal allocation_plans.quantity sum: {total_alloc:.0f}')

    # Resources deployed vs what's been deducted from inventory
    print('\nInventory snapshot (current):')
    inv = con.execute(text("SELECT depot_name, CAST(resource_type AS TEXT), quantity, unit FROM resource_items")).fetchall()
    for r in inv:
        print(f'  {r[0]:<28} {r[1]:<10} qty={r[2]:.1f} {r[3]}')

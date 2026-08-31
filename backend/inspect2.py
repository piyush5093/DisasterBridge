from sqlalchemy import create_engine, text
e = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
with e.connect() as con:
    # Mission columns
    c = con.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='missions' ORDER BY ordinal_position")).fetchall()
    print('missions cols:', [x[0] for x in c])

    # allocation_plans columns
    c2 = con.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='allocation_plans' ORDER BY ordinal_position")).fetchall()
    print('allocation_plans cols:', [x[0] for x in c2])

    # Mission sample with zone + event info
    mc = [x[0] for x in c]
    r = con.execute(text("""
        SELECT m.*, CAST(gc.severity_score AS TEXT) as sev, CAST(de.event_type AS TEXT) as etype, CAST(de.alert_level AS TEXT) as alev
        FROM missions m
        LEFT JOIN grid_cells gc ON m.zone_id = gc.id
        LEFT JOIN disaster_events de ON gc.related_event_id = de.id
        LIMIT 3
    """)).fetchall()
    for row in r:
        print('\nMission row:', dict(zip(list(mc) + ['sev','etype','alev'], row)))

    # Dashboard 13700 bug - what does it come from?
    inv = con.execute(text("SELECT resource_type::TEXT, quantity FROM resource_items")).fetchall()
    seeds = {'food': 5000, 'water': 8000, 'medical': 500, 'shelter': 200}
    print('\nInventory comparison:')
    total_deployed = 0
    for rt, qty in inv:
        if rt in seeds:
            deployed = seeds[rt] - qty
            total_deployed += deployed
            print(f'  {rt}: seed={seeds[rt]}, now={qty:.1f}, deployed={deployed:.1f}')
    print(f'  REAL total deployed: {total_deployed:.1f}')
    print(f'  Dashboard shows: 13700 (WRONG - this is summing seed values)')

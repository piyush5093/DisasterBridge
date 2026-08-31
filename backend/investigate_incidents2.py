from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
with engine.connect() as con:
    total = con.execute(text("SELECT count(*) FROM disaster_events")).scalar()
    with_extent = con.execute(text("SELECT count(*) FROM disaster_events WHERE impact_extent IS NOT NULL")).scalar()
    without_extent = con.execute(text("SELECT count(*) FROM disaster_events WHERE impact_extent IS NULL")).scalar()

    print(f"Total events: {total}")
    print(f"With impact_extent: {with_extent}")
    print(f"Without impact_extent (NULL): {without_extent}")

    # Check the classify endpoint requirements more carefully
    print("\n=== Sample events (first 5) ===")
    rows = con.execute(text("""
        SELECT id, source, alert_level, 
               impact_extent IS NOT NULL as has_extent,
               ST_X(location::geometry) as lng, ST_Y(location::geometry) as lat
        FROM disaster_events ORDER BY event_time DESC LIMIT 5
    """)).fetchall()
    for r in rows:
        print(f"  id={str(r[0])[:8]}... source={r[1]} alert={r[2]} has_extent={r[3]} lat={r[5]:.3f} lng={r[4]:.3f}")

    print("\n=== Alert level breakdown ===")
    rows2 = con.execute(text("SELECT alert_level, count(*) FROM disaster_events GROUP BY alert_level ORDER BY count(*) DESC")).fetchall()
    for r in rows2:
        print(f"  {r[0]}: {r[1]}")

    print("\n=== Orange/Red events sample ===")
    rows3 = con.execute(text("""
        SELECT id, raw_payload->>'title', alert_level, ST_X(location::geometry), ST_Y(location::geometry)
        FROM disaster_events WHERE alert_level IN ('red','orange') ORDER BY alert_level DESC LIMIT 10
    """)).fetchall()
    for r in rows3:
        print(f"  [{r[2]}] {r[1]} | lat={r[4]:.3f} lng={r[3]:.3f} | id={str(r[0])[:8]}...")

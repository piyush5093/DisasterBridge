from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
with engine.connect() as con:
    print("=== disaster_events total ===")
    total = con.execute(text("SELECT count(*) FROM disaster_events")).scalar()
    print(f"  Total: {total}")

    print("\n=== disaster_events GROUP BY alert_level ===")
    rows = con.execute(text("SELECT alert_level, count(*) FROM disaster_events GROUP BY alert_level ORDER BY count(*) DESC")).fetchall()
    running = 0
    for r in rows:
        print(f"  alert_level='{r[0]}' -> {r[1]}")
        running += r[1]
    print(f"  SUM: {running}")

    print("\n=== grid_cells total ===")
    gc = con.execute(text("SELECT count(*) FROM grid_cells")).scalar()
    print(f"  Total: {gc}")

    print("\n=== grid_cells GROUP BY priority ===")
    rows2 = con.execute(text("SELECT priority, count(*) FROM grid_cells GROUP BY priority ORDER BY count(*) DESC")).fetchall()
    for r in rows2:
        print(f"  priority='{r[0]}' -> {r[1]}")

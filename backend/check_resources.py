from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
with engine.connect() as con:
    print("=== Current resource_items ===")
    rows = con.execute(text("SELECT id, depot_name, CAST(resource_type AS TEXT), quantity, status FROM resource_items ORDER BY depot_name")).fetchall()
    for r in rows:
        print(f"  {r[1]} | type={r[2]} | qty={r[3]:.0f} | {r[4]}")

    print("\n=== Valid enum values for resourcetype ===")
    enum_vals = con.execute(text("SELECT unnest(enum_range(NULL::resourcetype))")).fetchall()
    for v in enum_vals:
        print(f"  {v[0]}")

    print("\n=== Shelter rows exist? ===")
    shelter = con.execute(text("SELECT COUNT(*) FROM resource_items WHERE CAST(resource_type AS TEXT) = 'shelter'")).scalar()
    print(f"  shelter rows: {shelter}")

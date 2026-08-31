from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
with engine.connect() as con:
    # Find actual column type for resource_type
    col_type = con.execute(text("""
        SELECT data_type, udt_name 
        FROM information_schema.columns 
        WHERE table_name = 'resource_items' AND column_name = 'resource_type'
    """)).fetchone()
    print(f"resource_type column type: {col_type}")

    # Find column type for allocation_plans
    col_type2 = con.execute(text("""
        SELECT data_type, udt_name 
        FROM information_schema.columns 
        WHERE table_name = 'allocation_plans' AND column_name = 'resource_type'
    """)).fetchone()
    print(f"allocation_plans.resource_type column type: {col_type2}")

    # Check distinct values in resource_items
    vals = con.execute(text("SELECT DISTINCT CAST(resource_type AS TEXT) FROM resource_items")).fetchall()
    print(f"Distinct resource_type in resource_items: {[v[0] for v in vals]}")

    # Seed shelter depot
    print("\nSeeding shelter depot...")
    con.execute(text("""
        INSERT INTO resource_items (id, resource_type, quantity, unit, status, location, depot_name)
        VALUES (
            gen_random_uuid(),
            'shelter',
            200,
            'units',
            'available',
            ST_SetSRID(ST_MakePoint(139.6, 35.7), 4326),
            'Yokohama Shelter Hub'
        )
    """))
    con.commit()

    # Verify
    rows = con.execute(text("SELECT depot_name, CAST(resource_type AS TEXT), quantity, status FROM resource_items ORDER BY depot_name")).fetchall()
    print("\nresource_items after seeding:")
    for r in rows:
        print(f"  {r[0]} | {r[1]} | qty={r[2]:.0f} | {r[3]}")

from sqlalchemy import create_engine, text

engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')

with engine.connect() as con:
    # --- Step 1: Clear transactional tables ---
    print("Clearing missions...")
    con.execute(text("DELETE FROM missions"))
    
    print("Clearing allocation_plans...")
    con.execute(text("DELETE FROM allocation_plans"))
    
    print("Clearing routes...")
    con.execute(text("DELETE FROM routes"))
    
    print("Clearing prediction_records...")
    con.execute(text("DELETE FROM prediction_records"))

    # --- Step 2: Reset modified fields on grid_cells ---
    print("Resetting grid_cells overrides and predicted demand fields...")
    con.execute(text("""
        UPDATE grid_cells SET
            priority_override = NULL,
            predicted_demand_food = NULL,
            predicted_demand_water = NULL,
            predicted_demand_medical = NULL,
            predicted_demand_shelter = NULL
    """))

    # --- Step 2b: Reset resource_items to realistic quantities ---
    # Check current state first
    rows = con.execute(text("SELECT id, depot_name, resource_type, quantity, status FROM resource_items ORDER BY depot_name")).fetchall()
    print("\nCurrent resource_items BEFORE reset:")
    for r in rows:
        print(f"  {r[1]} | {r[2]} | qty={r[3]:.2f} | status={r[4]}")

    # Reset all resources to available with realistic values per type
    con.execute(text("""
        UPDATE resource_items SET quantity = 5000, status = 'available'
        WHERE CAST(resource_type AS TEXT) = 'food'
    """))
    con.execute(text("""
        UPDATE resource_items SET quantity = 8000, status = 'available'
        WHERE CAST(resource_type AS TEXT) = 'water'
    """))
    con.execute(text("""
        UPDATE resource_items SET quantity = 500, status = 'available'
        WHERE CAST(resource_type AS TEXT) = 'medical'
    """))
    con.execute(text("""
        UPDATE resource_items SET quantity = 200, status = 'available'
        WHERE CAST(resource_type AS TEXT) = 'shelter'
    """))

    # Verify
    rows_after = con.execute(text("SELECT id, depot_name, resource_type, quantity, status FROM resource_items ORDER BY depot_name")).fetchall()
    print("\nresource_items AFTER reset:")
    for r in rows_after:
        print(f"  {r[1]} | {r[2]} | qty={r[3]:.0f} | status={r[4]}")

    con.commit()

    # --- Step 4: Confirm final row counts ---
    print("\n--- Final Row Counts ---")
    tables = ['disaster_events', 'grid_cells', 'resource_items', 'missions', 'allocation_plans', 'routes', 'prediction_records']
    for t in tables:
        count = con.execute(text(f"SELECT count(*) FROM {t}")).scalar()
        print(f"  {t}: {count}")

print("\nDone. Database reset complete.")

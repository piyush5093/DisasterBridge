from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
with engine.connect() as con:
    # Also clear allocation_plans so we start clean
    con.execute(text("DELETE FROM missions"))
    con.execute(text("DELETE FROM allocation_plans"))
    con.execute(text("DELETE FROM routes"))
    # Reset inventory
    con.execute(text("""
        UPDATE resource_items SET quantity = CASE
            WHEN depot_name = 'Chiba Warehouse'    THEN 5000
            WHEN depot_name = 'Tokyo Base'         THEN 8000
            WHEN depot_name = 'Saitama Medical Hub' THEN 500
            WHEN depot_name = 'Yokohama Shelter Hub' THEN 200
        END, status = 'available'
    """))
    con.commit()
    rows = con.execute(text(
        "SELECT depot_name, CAST(resource_type AS TEXT), quantity, status FROM resource_items ORDER BY depot_name"
    )).fetchall()
    print("Inventory reset:")
    for r in rows:
        print(f"  {r[0]:<30} {r[1]:<10} qty={r[2]:.0f} {r[3]}")

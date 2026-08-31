from sqlalchemy import create_engine, text
e = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
with e.connect() as con:
    cols = con.execute(text(
        "SELECT column_name, data_type FROM information_schema.columns WHERE table_name='resource_items' ORDER BY ordinal_position"
    )).fetchall()
    print("resource_items columns:")
    for c in cols:
        print(f"  {c[0]}: {c[1]}")
    
    # Sample row
    row = con.execute(text("SELECT * FROM resource_items LIMIT 1")).fetchone()
    print(f"\nSample row: {dict(zip([c[0] for c in cols], row))}")

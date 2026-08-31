from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
with engine.connect() as con:
    # Check the actual enum values in resourcetypeenum
    enum_vals = con.execute(text("""
        SELECT enumlabel FROM pg_enum 
        JOIN pg_type ON pg_enum.enumtypid = pg_type.oid 
        WHERE pg_type.typname = 'resourcetypeenum'
        ORDER BY enumsortorder
    """)).fetchall()
    print("Enum values:", [v[0] for v in enum_vals])

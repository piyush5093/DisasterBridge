from sqlalchemy import create_engine, text
e = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
with e.connect() as con:
    cols = con.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='missions' ORDER BY ordinal_position")).fetchall()
    print("missions columns:", [r[0] for r in cols])

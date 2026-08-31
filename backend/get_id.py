from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
with engine.connect() as con:
    print(str(con.execute(text("SELECT id FROM disaster_events LIMIT 1")).fetchone()[0]))

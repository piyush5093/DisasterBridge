from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
with engine.connect() as con:
    con.execute(text("UPDATE routes SET road_status = 'blocked' WHERE id IN (SELECT id FROM routes LIMIT 1)"))
    con.commit()

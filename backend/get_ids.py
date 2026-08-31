from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
with engine.connect() as con:
    rows = con.execute(text(
        "SELECT id, alert_level FROM disaster_events WHERE alert_level IN ('green','orange','red') ORDER BY alert_level DESC LIMIT 10"
    )).fetchall()
    for r in rows:
        print(f"{r[1]}: {r[0]}")

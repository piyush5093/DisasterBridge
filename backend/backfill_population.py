import psycopg2
conn = psycopg2.connect('postgresql://postgres:postgres@localhost:5432/postgres')
cur = conn.cursor()

# Get all event ids
cur.execute("SELECT id FROM disaster_events")
event_ids = [r[0] for r in cur.fetchall()]
print(f"Processing {len(event_ids)} events...")

import sys
sys.path.append('D:\\Disaster\\backend')
import services
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

for idx, eid in enumerate(event_ids):
    try:
        # compute impact extent
        services.compute_impact_extent(db, eid)
        # compute pop
        services.compute_population_exposure(db, eid)
        # compute buildings
        services.compute_building_footprint(db, eid)
        if idx % 50 == 0:
            print(f"  Done {idx}")
    except Exception as e:
        print(f"Error on {eid}: {e}")

# Now update grid_cells to inherit from disaster_events
cur.execute("""
    UPDATE grid_cells
    SET population_exposed = de.population_exposed
    FROM disaster_events de
    WHERE grid_cells.related_event_id = de.id
""")
conn.commit()

cur.execute('SELECT COALESCE(SUM(population_exposed), 0) FROM grid_cells')
print('Grid cells population exposed:', cur.fetchone()[0])

cur.execute('SELECT COALESCE(SUM(population_exposed), 0) FROM disaster_events')
print('Disaster events population exposed:', cur.fetchone()[0])

cur.close()
conn.close()
db.close()
print("Done!")

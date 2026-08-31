"""
Reset DB to India scope:
1. Clear test data (missions, routes, allocation_plans, grid_cells, disaster_events)
2. Relocate depots from Japan -> India
3. Reset inventory quantities
"""
import psycopg2

conn = psycopg2.connect('postgresql://postgres:postgres@localhost:5432/postgres')
conn.autocommit = False
cur = conn.cursor()

print("=== Step 1: Clear test data (FK-safe order) ===")

# prediction_records -> missions -> routes -> allocation_plans -> grid_cells -> disaster_events
cur.execute("DELETE FROM prediction_records")
print(f"  prediction_records cleared: {cur.rowcount}")

# null out volunteer zone assignments before clearing grid_cells
cur.execute("UPDATE volunteers SET zone_id = NULL WHERE zone_id IS NOT NULL")
print(f"  volunteers zone_id nulled: {cur.rowcount}")

cur.execute("DELETE FROM missions")
print(f"  missions cleared: {cur.rowcount}")

cur.execute("DELETE FROM routes")
print(f"  routes cleared: {cur.rowcount}")

cur.execute("DELETE FROM allocation_plans")
print(f"  allocation_plans cleared: {cur.rowcount}")

cur.execute("DELETE FROM grid_cells")
print(f"  grid_cells cleared: {cur.rowcount}")

cur.execute("DELETE FROM disaster_events")
print(f"  disaster_events cleared: {cur.rowcount}")

print("")
print("=== Step 2: Relocate depots to India ===")

# Map: old depot name -> (new name, city, resource_type, lat, lon, qty, unit)
depots = [
    # (old_name, new_name, resource_type, lat, lon, new_qty, unit)
    ("Chiba Warehouse",    "Delhi Coordination Hub",  "food",     28.6139, 77.2090, 10000, "kg"),
    ("Tokyo Base",         "Mumbai Relief Base",       "water",    19.0760, 72.8777, 15000, "liters"),
    ("Saitama Medical Hub","Kolkata Medical Centre",   "medical",  22.5726, 88.3639, 800,   "kits"),
    ("Yokohama Shelter Hub","Chennai Shelter Depot",   "shelter",  13.0827, 80.2707, 500,   "units"),
    ("Food Hub",           "Hyderabad Supply Hub",     "food",     17.3850, 78.4867, 8000,  "kg"),
]

for old_name, new_name, rtype, lat, lon, qty, unit in depots:
    cur.execute("""
        UPDATE resource_items
        SET depot_name = %s,
            resource_type = %s,
            location = ST_SetSRID(ST_MakePoint(%s, %s), 4326),
            quantity = %s,
            unit = %s,
            status = 'available',
            updated_at = NOW()
        WHERE depot_name = %s
    """, (new_name, rtype, lon, lat, qty, unit, old_name))
    print(f"  {old_name} -> {new_name} (lat={lat}, lon={lon}) rows={cur.rowcount}")

conn.commit()
print("")
print("=== Verification ===")
cur.execute("SELECT depot_name, resource_type, quantity, unit, ST_Y(location::geometry) as lat, ST_X(location::geometry) as lon, status FROM resource_items")
for r in cur.fetchall():
    print(f"  {r[0]} | {r[1]} | qty={r[2]} {r[3]} | lat={r[4]:.4f} lon={r[5]:.4f} | {r[6]}")

cur.execute("SELECT count(*) FROM disaster_events")
print(f"disaster_events remaining: {cur.fetchone()[0]}")

cur.close()
conn.close()
print("DONE")

import psycopg2, uuid
conn = psycopg2.connect('postgresql://postgres:postgres@localhost:5432/postgres')
conn.autocommit = False
cur = conn.cursor()

# Insert Mumbai Hygiene Hub
new_id = str(uuid.uuid4())
cur.execute("""
    INSERT INTO resource_items (id, resource_type, quantity, unit, location, depot_name, status, updated_at)
    VALUES (
        %s,
        'hygiene_kits',
        2000,
        'kits',
        ST_SetSRID(ST_MakePoint(72.8777, 19.0760), 4326),
        'Mumbai Hygiene Hub',
        'available',
        NOW()
    )
""", (new_id,))
print(f"Inserted Mumbai Hygiene Hub id={new_id[:8]}...")

conn.commit()

print("")
print("=== Final depot state ===")
cur.execute("SELECT depot_name, resource_type::text, quantity, unit, status, ST_Y(location::geometry)::numeric(7,4) as lat, ST_X(location::geometry)::numeric(7,4) as lon FROM resource_items ORDER BY depot_name")
for r in cur.fetchall():
    print(f"  {r[0]} | {r[1]} | {r[2]} {r[3]} | lat={r[5]} lon={r[6]} | {r[4]}")

cur.close()
conn.close()
print("DONE")

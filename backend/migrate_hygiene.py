"""
Migrate: water -> hygiene_kits, food unit kg -> packages
"""
import psycopg2

conn = psycopg2.connect('postgresql://postgres:postgres@localhost:5432/postgres')
conn.autocommit = False
cur = conn.cursor()

print("=== 1. Rename enum value: water -> hygiene_kits ===")
cur.execute("ALTER TYPE resourcetypeenum RENAME VALUE 'water' TO 'hygiene_kits'")
print("  Done")

print("=== 2. Rename grid_cells column ===")
cur.execute("ALTER TABLE grid_cells RENAME COLUMN predicted_demand_water TO predicted_demand_hygiene_kits")
print("  Done")

print("=== 3. Rename prediction_records column ===")
cur.execute("ALTER TABLE prediction_records RENAME COLUMN predicted_water TO predicted_hygiene_kits")
print("  Done")

print("=== 4. Update resource_items units ===")
cur.execute("UPDATE resource_items SET unit='kits', quantity=2000, depot_name='Mumbai Hygiene Hub' WHERE resource_type='hygiene_kits'")
print(f"  hygiene_kits unit updated: {cur.rowcount} rows")

cur.execute("UPDATE resource_items SET unit='packages' WHERE resource_type='food'")
print(f"  food unit -> packages: {cur.rowcount} rows")

conn.commit()

print("")
print("=== Verification ===")
cur.execute("SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_type.oid = pg_enum.enumtypid WHERE pg_type.typname ILIKE '%resource%'")
print("resource_type enum:", [r[0] for r in cur.fetchall()])
cur.execute("SELECT depot_name, resource_type, quantity, unit, status FROM resource_items ORDER BY resource_type")
for r in cur.fetchall():
    print(f"  {r[0]} | {r[1]} | {r[2]} {r[3]} | {r[4]}")

cur.close()
conn.close()
print("DONE")

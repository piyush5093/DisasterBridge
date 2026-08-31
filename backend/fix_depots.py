import psycopg2
conn = psycopg2.connect('postgresql://postgres:postgres@localhost:5432/postgres')
cur = conn.cursor()
cur.execute("SELECT id, depot_name, resource_type::text, quantity, unit, status FROM resource_items ORDER BY depot_name")
rows = cur.fetchall()
print(f"Total resource_items: {len(rows)}")
for r in rows:
    print(f"  id={str(r[0])[:8]}... {r[1]} | type={r[2]} | qty={r[3]:.1f} {r[4]} | {r[5]}")

# Fix: update hygiene_kits row and reset all quantities
print("")
print("Resetting quantities and fixing hygiene_kits depot...")
cur.execute("UPDATE resource_items SET unit='kits', quantity=2000, depot_name='Mumbai Hygiene Hub', status='available' WHERE resource_type::text='hygiene_kits'")
print(f"  hygiene_kits update: {cur.rowcount}")

cur.execute("UPDATE resource_items SET quantity=10000, status='available' WHERE depot_name='Delhi Coordination Hub'")
cur.execute("UPDATE resource_items SET quantity=8000, status='available' WHERE depot_name='Hyderabad Supply Hub'")
cur.execute("UPDATE resource_items SET quantity=800, status='available' WHERE depot_name='Kolkata Medical Centre'")
cur.execute("UPDATE resource_items SET quantity=500, status='available' WHERE depot_name='Chennai Shelter Depot'")
conn.commit()

print("")
print("Final state:")
cur.execute("SELECT depot_name, resource_type::text, quantity, unit, status FROM resource_items ORDER BY depot_name")
for r in cur.fetchall():
    print(f"  {r[0]} | {r[1]} | {r[2]} {r[3]} | {r[4]}")

cur.close()
conn.close()

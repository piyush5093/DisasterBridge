import psycopg2
conn = psycopg2.connect('postgresql://postgres:postgres@localhost:5432/postgres')
cur = conn.cursor()

cur.execute("SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_type.oid = pg_enum.enumtypid WHERE pg_type.typname ILIKE '%resource%'")
print('resource_type enum:', [r[0] for r in cur.fetchall()])

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='grid_cells' AND column_name LIKE '%water%' OR table_name='grid_cells' AND column_name LIKE '%hygiene%'")
print('grid_cells water/hygiene cols:', [r[0] for r in cur.fetchall()])

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='prediction_records'")
print('prediction_records cols:', [r[0] for r in cur.fetchall()])

cur.close()
conn.close()

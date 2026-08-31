import psycopg2

conn = psycopg2.connect('postgresql://postgres:postgres@localhost:5432/postgres')
conn.autocommit = False
cur = conn.cursor()

# Find actual enum name used for resource_type
cur.execute("""
    SELECT pg_type.typname
    FROM pg_enum
    JOIN pg_type ON pg_type.oid = pg_enum.enumtypid
    WHERE enumlabel = 'water'
""")
rows = cur.fetchall()
print("Enum types containing 'water':", rows)

# Also check the column's actual type
cur.execute("""
    SELECT column_name, udt_name
    FROM information_schema.columns
    WHERE table_name = 'resource_items' AND column_name = 'resource_type'
""")
print("resource_items.resource_type type:", cur.fetchall())

cur.close()
conn.close()

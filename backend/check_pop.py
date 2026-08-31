import psycopg2
conn = psycopg2.connect('postgresql://postgres:postgres@localhost:5432/postgres')
cur = conn.cursor()
cur.execute("SELECT alert_level, COUNT(*), COALESCE(SUM(population_exposed),0) FROM disaster_events GROUP BY alert_level ORDER BY 2 DESC")
for r in cur.fetchall():
    print(f"  {r[0]} | count={r[1]} | pop={int(r[2]):,}")
cur.close()
conn.close()

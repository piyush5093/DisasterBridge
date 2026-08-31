from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
with engine.connect() as con:
    print("=== Severity score distribution ===")
    row = con.execute(text("SELECT MIN(severity_score), MAX(severity_score), AVG(severity_score), PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY severity_score) as median FROM grid_cells")).fetchone()
    print(f"  MIN={row[0]:.2f}  MAX={row[1]:.2f}  AVG={row[2]:.2f}  MEDIAN={row[3]:.2f}")

    print("\n=== Priority distribution BEFORE fix ===")
    rows = con.execute(text("SELECT priority, count(*), MIN(severity_score), MAX(severity_score) FROM grid_cells GROUP BY priority ORDER BY MIN(severity_score) DESC")).fetchall()
    for r in rows:
        print(f"  priority={r[0]}  count={r[1]}  min_sev={r[2]:.1f}  max_sev={r[3]:.1f}")

    print("\n=== Full severity list ===")
    rows2 = con.execute(text("SELECT id, severity_score, CAST(priority AS TEXT) FROM grid_cells ORDER BY severity_score DESC")).fetchall()
    for r in rows2:
        print(f"  id={str(r[0])[:8]}...  sev={r[1]:.1f}  priority={r[2]}")

    print("\n=== Percentile breakpoints ===")
    pct = con.execute(text("""
        SELECT 
            PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY severity_score) as p10,
            PERCENTILE_CONT(0.33) WITHIN GROUP (ORDER BY severity_score) as p33,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY severity_score) as p50,
            PERCENTILE_CONT(0.67) WITHIN GROUP (ORDER BY severity_score) as p67,
            PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY severity_score) as p90
        FROM grid_cells
    """)).fetchone()
    print(f"  p10={pct[0]:.1f}  p33={pct[1]:.1f}  p50={pct[2]:.1f}  p67={pct[3]:.1f}  p90={pct[4]:.1f}")

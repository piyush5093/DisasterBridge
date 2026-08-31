from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')

# Thresholds match services_phase3.py exactly
HIGH_THRESH = 60.0
MED_THRESH  = 22.0

with engine.connect() as con:
    print("=== BEFORE recalibration ===")
    rows = con.execute(text(
        "SELECT id, severity_score, CAST(priority AS TEXT) FROM grid_cells ORDER BY severity_score DESC"
    )).fetchall()
    for r in rows:
        print(f"  sev={r[1]:.1f}  priority={r[2]}")

    # Recalibrate in-place using SQL CASE
    con.execute(text(f"""
        UPDATE grid_cells SET priority = CASE
            WHEN severity_score >= {HIGH_THRESH} THEN 'high'::priorityenum
            WHEN severity_score >= {MED_THRESH}  THEN 'medium'::priorityenum
            ELSE 'low'::priorityenum
        END
    """))
    con.commit()

    print("\n=== AFTER recalibration ===")
    rows2 = con.execute(text(
        "SELECT id, severity_score, CAST(priority AS TEXT) FROM grid_cells ORDER BY severity_score DESC"
    )).fetchall()
    for r in rows2:
        print(f"  sev={r[1]:.1f}  priority={r[2]}")

    print("\n=== Distribution AFTER ===")
    dist = con.execute(text(
        "SELECT CAST(priority AS TEXT), count(*), MIN(severity_score), MAX(severity_score) FROM grid_cells GROUP BY priority ORDER BY MIN(severity_score) DESC"
    )).fetchall()
    for r in dist:
        print(f"  priority={r[0]}  count={r[1]}  min_sev={r[2]:.1f}  max_sev={r[3]:.1f}")

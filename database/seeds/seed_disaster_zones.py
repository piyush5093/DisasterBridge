"""
Step 3 -- Seed Disaster Zones from Real Datasets
=================================================
Reads processed CSVs from Step 1 & Step 2 and seeds the DB with
real disaster zones from:
  - Kerala Floods 2018  (district_wise_details.csv  -> kerala_processed.csv)
  - Chennai Floods 2015 (46d6c279-....kml           -> chennai_flood_zones.csv)

Run from project root:
  python database/seeds/seed_disaster_zones.py
"""

import sys
import os

# -- Path setup: add backend to sys.path ------------------------------------
_here    = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.abspath(os.path.join(_here, "..", "..", "backend"))
_root    = os.path.abspath(os.path.join(_here, "..", ".."))
sys.path.insert(0, _backend)

import pandas as pd
from pathlib import Path

from app.db.database import SessionLocal, engine, Base
from app.models.zone import DisasterZone

# -- Paths -------------------------------------------------------------------
ROOT          = Path(_root)
KERALA_CSV    = ROOT / "ml_engine" / "data" / "processed" / "kerala_processed.csv"
CHENNAI_CSV   = ROOT / "ml_engine" / "data" / "processed" / "chennai_flood_zones.csv"

# -- Kerala district coordinates (centroid approximations) -------------------
KERALA_COORDS = {
    "Thiruvananthapuram": (8.5241,  76.9366),
    "Kollam":             (8.8932,  76.6141),
    "Pathanamthitta":     (9.2648,  76.7870),
    "Alappuzha":          (9.4981,  76.3388),
    "Kottayam":           (9.5916,  76.5222),
    "Idukki":             (9.9189,  77.1025),
    "Ernakulam":          (10.0161, 76.3419),
    "Thrissur":           (10.5276, 76.2144),
    "Palakkad":           (10.7867, 76.6548),
    "Malappuram":         (11.0730, 76.0740),
    "Kozhikode":          (11.2588, 75.7804),
    "Wayanad":            (11.6854, 76.1320),
    "Kannur":             (11.8745, 75.3704),
    "Kasaragode":         (12.4996, 74.9869),
}

# Severity mapping based on fatality + camp count
def _severity_from_row(row):
    score = (
        (row["fatalities"] / 72.0) * 4.0 +          # max fatalities = 72 (Thrissur)
        (row["no_of_camps"] / 4352.0) * 3.0 +       # max camps = 4352 (Pathanamthitta)
        (row["no_of_landslides"] / 143.0) * 2.0 +   # max landslides = 143 (Idukki)
        (row["rainfall_excess"] / 951.6) * 1.0       # max excess = Idukki
    )
    score = round(min(10.0, score * 10.0), 2)
    if score >= 8.0:   return "critical", score
    elif score >= 6.0: return "high",     score
    elif score >= 4.0: return "medium",   score
    else:              return "low",      max(1.0, score)


# ============================================================================
def seed_kerala_zones(db) -> int:
    print("\n[1/3] Seeding Kerala Floods 2018 zones...")

    if not KERALA_CSV.exists():
        print(f"      ERROR: {KERALA_CSV} not found. Run Step 1 first.")
        return 0

    df = pd.read_csv(KERALA_CSV)
    created = 0

    for _, row in df.iterrows():
        district = row["district"]
        source_id = f"kerala_2018_{district.lower().replace(' ', '_')}"

        # Skip if already seeded
        existing = db.query(DisasterZone).filter(
            DisasterZone.source_event_id == source_id
        ).first()
        if existing:
            print(f"      [SKIP] {district} already in DB")
            continue

        lat, lon = KERALA_COORDS.get(district, (10.0, 76.5))
        severity, score = _severity_from_row(row)

        # Estimated population affected: camps * avg 4 people per camp
        pop_affected = int(row["no_of_camps"]) * 4

        zone = DisasterZone(
            name                = f"Kerala 2018 -- {district}",
            state               = "Kerala",
            district            = district,
            latitude            = lat,
            longitude           = lon,
            area_sq_km          = 0.0,
            disaster_type       = "flood",
            severity            = severity,
            severity_score      = score,
            population_affected = pop_affected,
            population_total    = 0,
            vulnerability_index = round(
                min(1.0, row["no_of_landslides"] / 143.0 * 0.4 +
                         row["fatalities"]        / 72.0  * 0.6), 4
            ),
            source              = "kerala_dataset_2018",
            source_event_id     = source_id,
            description         = (
                f"Kerala Floods 2018 | {district} district | "
                f"Fatalities: {int(row['fatalities'])} | "
                f"Camps: {int(row['no_of_camps'])} | "
                f"Rainfall: {row['actual_rainfall_in_mm']}mm "
                f"(normal: {row['normal_rainfall_in_mm']}mm) | "
                f"Landslides: {int(row['no_of_landslides'])} | "
                f"Damaged houses: {int(row['full_damaged_houses'])}"
            ),
            is_active           = 1,
        )
        db.add(zone)
        created += 1
        print(f"      [ADD] {district:<20} severity={severity:<8} score={score}  pop~{pop_affected:,}")

    db.commit()
    print(f"\n      Kerala zones seeded: {created}")
    return created


# ============================================================================
def seed_chennai_zones(db) -> int:
    print("\n[2/3] Seeding Chennai Floods 2015 zones...")

    if not CHENNAI_CSV.exists():
        print(f"      ERROR: {CHENNAI_CSV} not found. Run Step 2 first.")
        return 0

    df = pd.read_csv(CHENNAI_CSV)
    created = 0

    for _, row in df.iterrows():
        source_id = f"chennai_2015_zone_{int(row['zone_id'])}"

        existing = db.query(DisasterZone).filter(
            DisasterZone.source_event_id == source_id
        ).first()
        if existing:
            print(f"      [SKIP] {row['name']} already in DB")
            continue

        # Population estimate: ~12,000/sq km for Chennai urban density
        density_per_sqkm = 12000
        pop_affected = int(min(row["area_sq_km"] * density_per_sqkm * 0.15, 500000))

        zone = DisasterZone(
            name                = row["name"],
            state               = row["state"],
            district            = row["district"],
            latitude            = float(row["center_lat"]),
            longitude           = float(row["center_lon"]),
            area_sq_km          = float(row["area_sq_km"]),
            disaster_type       = row["disaster_type"],
            severity            = row["severity"],
            severity_score      = float(row["severity_score"]),
            population_affected = pop_affected,
            population_total    = int(row["area_sq_km"] * density_per_sqkm),
            vulnerability_index = 0.45,   # urban flood default
            source              = row["source"],
            source_event_id     = source_id,
            description         = str(row["description"]),
            is_active           = 1,
        )
        db.add(zone)
        created += 1
        print(f"      [ADD] {row['name']:<25} severity={row['severity']:<8} area={row['area_sq_km']}km2  pop~{pop_affected:,}")

    db.commit()
    print(f"\n      Chennai zones seeded: {created}")
    return created


# ============================================================================
def print_summary(db):
    print("\n[3/3] DB Summary after seeding...")
    all_zones = db.query(DisasterZone).filter(DisasterZone.is_active == 1).all()

    from collections import Counter
    sev_counts = Counter(z.severity for z in all_zones)
    src_counts = Counter(
        "Kerala 2018"   if "kerala" in (z.source or "")  else
        "Chennai 2015"  if "chennai" in (z.source or "") else
        "Live/Manual"
        for z in all_zones
    )

    print(f"\n      Total active zones : {len(all_zones)}")
    print(f"\n      By severity:")
    for sev in ["critical", "high", "medium", "low"]:
        bar = "#" * sev_counts.get(sev, 0)
        print(f"        {sev:<10}: {sev_counts.get(sev, 0):>3}  {bar}")

    print(f"\n      By source:")
    for src, cnt in src_counts.items():
        print(f"        {src:<15}: {cnt}")

    total_pop = sum(z.population_affected for z in all_zones)
    print(f"\n      Total population affected: {total_pop:,}")


# ============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  AI Disaster Response -- Zone Seeder (Step 3)")
    print("=" * 60)

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        k = seed_kerala_zones(db)
        c = seed_chennai_zones(db)
        print_summary(db)

        print("\n" + "=" * 60)
        print("  [OK] Step 3 Complete!")
        print(f"  Kerala zones  added : {k}")
        print(f"  Chennai zones added : {c}")
        print(f"  Total new zones     : {k + c}")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"\n  [ERROR] {e}")
        raise
    finally:
        db.close()

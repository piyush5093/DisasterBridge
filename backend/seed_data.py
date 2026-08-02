"""
Seed Data Script — AI Disaster Response Management System
=========================================================
Populates the database with realistic demo data for India:
  - 5 Resource Depots (Delhi, Mumbai, Chennai, Kolkata, Hyderabad)
  - Resources per depot (food, water, medical, transport, shelter)
  - 8 Disaster Zones (Kerala, Odisha, Assam, Bihar, Gujarat...)
  - 6 Field Teams

Usage:
    cd backend
    python seed_data.py
"""

import sys
import os

# Add backend root to path so imports work
sys.path.insert(0, os.path.dirname(__file__))

from app.db.database import engine, Base, SessionLocal
from app.models.zone import DisasterZone
from app.models.resource import Resource
from app.models.depot import Depot
from app.models.event import FieldTeam


def seed_all():
    # Create tables if not exist
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # ── Check if already seeded ──────────────────────────────────────────
        if db.query(Depot).count() > 0:
            print("[SEED] Database already has data. Use --force to re-seed.")
            if "--force" not in sys.argv:
                return

            print("[SEED] --force flag detected. Clearing existing data...")
            db.query(FieldTeam).delete()
            db.query(Resource).delete()
            db.query(Depot).delete()
            db.query(DisasterZone).delete()
            db.commit()

        # ── 1. DEPOTS ────────────────────────────────────────────────────────
        print("[SEED] Creating depots...")
        depots_data = [
            {
                "name": "Delhi National HQ Depot",
                "city": "New Delhi", "state": "Delhi",
                "latitude": 28.6139, "longitude": 77.2090,
                "capacity_units": 500000,
                "contact_name": "Rajesh Kumar", "contact_phone": "+91-11-23456789",
            },
            {
                "name": "Mumbai Western Region Depot",
                "city": "Mumbai", "state": "Maharashtra",
                "latitude": 19.0760, "longitude": 72.8777,
                "capacity_units": 400000,
                "contact_name": "Priya Sharma", "contact_phone": "+91-22-23456789",
            },
            {
                "name": "Chennai Southern Zone Depot",
                "city": "Chennai", "state": "Tamil Nadu",
                "latitude": 13.0827, "longitude": 80.2707,
                "capacity_units": 350000,
                "contact_name": "Anand Rajan", "contact_phone": "+91-44-23456789",
            },
            {
                "name": "Kolkata Eastern Region Depot",
                "city": "Kolkata", "state": "West Bengal",
                "latitude": 22.5726, "longitude": 88.3639,
                "capacity_units": 300000,
                "contact_name": "Subhas Banerjee", "contact_phone": "+91-33-23456789",
            },
            {
                "name": "Hyderabad Central Depot",
                "city": "Hyderabad", "state": "Telangana",
                "latitude": 17.3850, "longitude": 78.4867,
                "capacity_units": 350000,
                "contact_name": "Kavitha Reddy", "contact_phone": "+91-40-23456789",
            },
        ]

        depot_objs = []
        for d in depots_data:
            depot = Depot(**d)
            db.add(depot)
            depot_objs.append(depot)
        db.commit()
        # Refresh to get IDs
        for d in depot_objs:
            db.refresh(d)

        depot_ids = {d.city: d.id for d in depot_objs}
        print(f"  Created {len(depot_objs)} depots")

        # ── 2. RESOURCES ─────────────────────────────────────────────────────
        print("[SEED] Creating resources...")

        resources_template = [
            # (name, category, unit, total, available, deployed, threshold)
            ("Food Packets (3-day)",     "food",      "packets",  200000, 165000, 35000, 0.20),
            ("Drinking Water (500ml)",   "water",     "liters",   500000, 410000, 90000, 0.20),
            ("Medical Emergency Kit",    "medical",   "kits",     10000,   8200,  1800, 0.25),
            ("Relief Shelter Tents",     "shelter",   "units",     5000,   4100,   900, 0.20),
            ("Rescue Trucks (4T)",       "transport", "vehicles",    80,     60,    20, 0.25),
            ("Blankets",                 "shelter",   "units",    20000,  16000,  4000, 0.20),
            ("ORS Packets",              "medical",   "packets",  50000,  42000,  8000, 0.20),
            ("Portable Water Purifier",  "water",     "units",      200,    165,    35, 0.20),
        ]

        for city, depot_id in depot_ids.items():
            for (name, cat, unit, total, avail, deployed, threshold) in resources_template:
                # Scale quantities by depot capacity rank
                scale = {"New Delhi": 1.0, "Mumbai": 0.8, "Chennai": 0.7, "Kolkata": 0.65, "Hyderabad": 0.7}.get(city, 0.7)
                r = Resource(
                    name=name,
                    category=cat,
                    unit=unit,
                    quantity_total=int(total * scale),
                    quantity_available=int(avail * scale),
                    quantity_deployed=int(deployed * scale),
                    depot_id=depot_id,
                    critical_threshold=threshold,
                )
                db.add(r)

        db.commit()
        resource_count = db.query(Resource).count()
        print(f"  Created {resource_count} resource items across {len(depot_objs)} depots")

        # ── 3. DISASTER ZONES ────────────────────────────────────────────────
        print("[SEED] Creating disaster zones...")
        zones_data = [
            {
                "name": "Kerala — Wayanad Flood Zone",
                "state": "Kerala", "district": "Wayanad",
                "latitude": 11.6854, "longitude": 76.1320,
                "area_sq_km": 2131.0,
                "disaster_type": "flood",
                "severity": "critical", "severity_score": 9.2,
                "population_affected": 182000, "population_total": 817000,
                "vulnerability_index": 0.72,
                "source": "ndma", "source_event_id": "KL-2024-WY-001",
                "description": "Severe flooding in Wayanad due to heavy monsoon rains. Multiple villages cut off.",
            },
            {
                "name": "Odisha — Puri Cyclone Zone",
                "state": "Odisha", "district": "Puri",
                "latitude": 19.8132, "longitude": 85.8314,
                "area_sq_km": 3479.0,
                "disaster_type": "cyclone",
                "severity": "high", "severity_score": 7.8,
                "population_affected": 95000, "population_total": 1500000,
                "vulnerability_index": 0.61,
                "source": "ndma", "source_event_id": "OR-2024-PU-002",
                "description": "Cyclone Remal aftermath — coastal flooding, infrastructure damage.",
            },
            {
                "name": "Assam — Brahmaputra River Flood",
                "state": "Assam", "district": "Dhubri",
                "latitude": 26.0020, "longitude": 89.9774,
                "area_sq_km": 2815.0,
                "disaster_type": "flood",
                "severity": "critical", "severity_score": 8.5,
                "population_affected": 246000, "population_total": 1400000,
                "vulnerability_index": 0.68,
                "source": "ndma", "source_event_id": "AS-2024-DB-003",
                "description": "Brahmaputra breached banks — annual flood worse than usual due to upstream dam discharge.",
            },
            {
                "name": "Gujarat — Kutch Earthquake Zone",
                "state": "Gujarat", "district": "Kutch",
                "latitude": 23.2420, "longitude": 69.6669,
                "area_sq_km": 45652.0,
                "disaster_type": "earthquake",
                "severity": "medium", "severity_score": 5.5,
                "population_affected": 28000, "population_total": 2100000,
                "vulnerability_index": 0.44,
                "source": "usgs", "source_event_id": "usp000jq01",
                "description": "M5.2 earthquake near Bhuj. Structural damage to older buildings.",
            },
            {
                "name": "Uttarakhand — Chamoli Landslide",
                "state": "Uttarakhand", "district": "Chamoli",
                "latitude": 30.4086, "longitude": 79.3100,
                "area_sq_km": 784.0,
                "disaster_type": "landslide",
                "severity": "high", "severity_score": 7.2,
                "population_affected": 14500, "population_total": 390000,
                "vulnerability_index": 0.79,
                "source": "ndma", "source_event_id": "UT-2024-CH-005",
                "description": "Flash flood-triggered landslide blocks NH-7 highway. Villages isolated.",
            },
            {
                "name": "Bihar — Kosi River Flooding",
                "state": "Bihar", "district": "Supaul",
                "latitude": 26.1203, "longitude": 86.6027,
                "area_sq_km": 2410.0,
                "disaster_type": "flood",
                "severity": "high", "severity_score": 7.4,
                "population_affected": 78000, "population_total": 2200000,
                "vulnerability_index": 0.65,
                "source": "ndma", "source_event_id": "BH-2024-SP-006",
                "description": "Kosi River flood — annual event with worsening displacement this year.",
            },
            {
                "name": "Tamil Nadu — Chennai Coastal Flood",
                "state": "Tamil Nadu", "district": "Chennai",
                "latitude": 13.0827, "longitude": 80.2707,
                "area_sq_km": 174.0,
                "disaster_type": "flood",
                "severity": "medium", "severity_score": 5.8,
                "population_affected": 42000, "population_total": 7000000,
                "vulnerability_index": 0.38,
                "source": "gdacs", "source_event_id": "GDACS-FL-2024-TN-001",
                "description": "Heavy rainfall causing waterlogging in low-lying areas of Chennai.",
            },
            {
                "name": "Rajasthan — Barmer Drought Zone",
                "state": "Rajasthan", "district": "Barmer",
                "latitude": 25.7490, "longitude": 71.3936,
                "area_sq_km": 28387.0,
                "disaster_type": "drought",
                "severity": "low", "severity_score": 3.5,
                "population_affected": 11000, "population_total": 2500000,
                "vulnerability_index": 0.55,
                "source": "ndma", "source_event_id": "RJ-2024-BM-008",
                "description": "Prolonged deficit rainfall causing water scarcity in Barmer district.",
            },
        ]

        zone_objs = []
        for z in zones_data:
            zone = DisasterZone(**z)
            db.add(zone)
            zone_objs.append(zone)
        db.commit()
        for z in zone_objs:
            db.refresh(z)
        print(f"  Created {len(zone_objs)} disaster zones")

        # ── 4. FIELD TEAMS ───────────────────────────────────────────────────
        print("[SEED] Creating field teams...")
        teams_data = [
            {
                "team_code": "NDRF-Alpha-1",
                "team_name": "NDRF Alpha Response Team 1",
                "members": 45,
                "zone_id": zone_objs[0].id,   # Kerala
                "depot_id": depot_ids["Chennai"],
                "status": "deployed",
                "current_lat": 11.6900, "current_lon": 76.1400,
                "location_txt": "Wayanad, Kerala",
                "lead_name": "Maj. Arjun Singh", "lead_phone": "+91-99001-12345",
            },
            {
                "team_code": "SDRF-Odisha-3",
                "team_name": "Odisha SDRF Team 3",
                "members": 30,
                "zone_id": zone_objs[1].id,   # Odisha
                "depot_id": depot_ids["Kolkata"],
                "status": "deployed",
                "current_lat": 19.8200, "current_lon": 85.8300,
                "location_txt": "Puri, Odisha",
                "lead_name": "Cdr. Bikash Das", "lead_phone": "+91-99002-23456",
            },
            {
                "team_code": "NDRF-Bravo-2",
                "team_name": "NDRF Bravo Response Team 2",
                "members": 50,
                "zone_id": zone_objs[2].id,   # Assam
                "depot_id": depot_ids["Kolkata"],
                "status": "deployed",
                "current_lat": 26.0100, "current_lon": 89.9800,
                "location_txt": "Dhubri, Assam",
                "lead_name": "Col. Ravi Nair", "lead_phone": "+91-99003-34567",
            },
            {
                "team_code": "NDRF-Delta-4",
                "team_name": "NDRF Delta Medical Team",
                "members": 25,
                "zone_id": zone_objs[4].id,   # Uttarakhand
                "depot_id": depot_ids["New Delhi"],
                "status": "transit",
                "current_lat": 30.0000, "current_lon": 78.9000,
                "location_txt": "En route to Chamoli, Uttarakhand",
                "lead_name": "Dr. Meena Gupta", "lead_phone": "+91-99004-45678",
            },
            {
                "team_code": "SDRF-Bihar-5",
                "team_name": "Bihar SDRF Flood Relief Team",
                "members": 35,
                "zone_id": zone_objs[5].id,   # Bihar
                "depot_id": depot_ids["Kolkata"],
                "status": "deployed",
                "current_lat": 26.1300, "current_lon": 86.6100,
                "location_txt": "Supaul, Bihar",
                "lead_name": "Insp. Rajan Verma", "lead_phone": "+91-99005-56789",
            },
            {
                "team_code": "NDRF-Echo-6",
                "team_name": "NDRF Standby Reserve Team",
                "members": 40,
                "zone_id": None,
                "depot_id": depot_ids["Hyderabad"],
                "status": "standby",
                "current_lat": 17.3850, "current_lon": 78.4867,
                "location_txt": "Hyderabad Central Depot",
                "lead_name": "Cdr. Lakshmi Rao", "lead_phone": "+91-99006-67890",
            },
        ]

        for t in teams_data:
            team = FieldTeam(**t)
            db.add(team)
        db.commit()

        team_count = db.query(FieldTeam).count()
        print(f"  Created {team_count} field teams")

        # ── Summary ──────────────────────────────────────────────────────────
        print("\n[SEED] SUCCESS: Seeding complete!")
        print(f"  Depots   : {db.query(Depot).count()}")
        print(f"  Resources: {db.query(Resource).count()}")
        print(f"  Zones    : {db.query(DisasterZone).count()}")
        print(f"  Teams    : {db.query(FieldTeam).count()}")
        print("\n  Run the server: python run.py")
        print("  Swagger UI    : http://localhost:8000/docs")

    except Exception as e:
        db.rollback()
        print(f"[SEED] ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()

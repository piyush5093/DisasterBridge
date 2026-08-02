"""Seed script — populates DB with initial demo data matching disaster_demo.html"""

import sys, os
# Resolve path to backend folder regardless of where script is run from
_here    = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.join(_here, "..", "..", "backend")
sys.path.insert(0, os.path.abspath(_backend))

from app.db.database import SessionLocal, engine, Base
from app.models.zone     import DisasterZone
from app.models.resource import Resource
from app.models.depot    import Depot
from app.models.event    import FieldTeam

# Create tables first
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# ── DEPOTS ────────────────────────────────────────────────────────────────────
depots_data = [
    {"name": "Delhi HQ Depot",     "city": "New Delhi", "state": "Delhi",       "latitude": 28.6139,  "longitude": 77.2090,  "capacity_units": 200000},
    {"name": "Mumbai Depot",       "city": "Mumbai",    "state": "Maharashtra",  "latitude": 19.0760,  "longitude": 72.8777,  "capacity_units": 150000},
    {"name": "Hyderabad Depot",    "city": "Hyderabad", "state": "Telangana",    "latitude": 17.3850,  "longitude": 78.4867,  "capacity_units": 120000},
    {"name": "Kochi Depot",        "city": "Kochi",     "state": "Kerala",       "latitude": 9.9312,   "longitude": 76.2673,  "capacity_units": 80000},
    {"name": "Kolkata Depot",      "city": "Kolkata",   "state": "West Bengal",  "latitude": 22.5726,  "longitude": 88.3639,  "capacity_units": 100000},
]

for d in depots_data:
    if not db.query(Depot).filter(Depot.name == d["name"]).first():
        db.add(Depot(**d))

db.commit()
delhi_depot  = db.query(Depot).filter(Depot.city == "New Delhi").first()
mumbai_depot = db.query(Depot).filter(Depot.city == "Mumbai").first()

# ── DISASTER ZONES ────────────────────────────────────────────────────────────
zones_data = [
    {"name": "Kerala — Wayanad",          "state": "Kerala",      "district": "Wayanad",    "latitude": 11.6854,  "longitude": 76.1320,  "disaster_type": "flood",      "severity": "critical", "severity_score": 9.4, "population_affected": 18200, "vulnerability_index": 0.72, "source": "gdacs"},
    {"name": "Kerala — Idukki",           "state": "Kerala",      "district": "Idukki",     "latitude": 9.9189,   "longitude": 77.1025,  "disaster_type": "flood",      "severity": "critical", "severity_score": 8.9, "population_affected": 12700, "vulnerability_index": 0.65, "source": "gdacs"},
    {"name": "Odisha — Puri",             "state": "Odisha",      "district": "Puri",       "latitude": 19.8135,  "longitude": 85.8312,  "disaster_type": "cyclone",    "severity": "high",     "severity_score": 7.3, "population_affected": 9100,  "vulnerability_index": 0.55, "source": "gdacs"},
    {"name": "Odisha — Khurda",           "state": "Odisha",      "district": "Khurda",     "latitude": 20.1736,  "longitude": 85.6314,  "disaster_type": "cyclone",    "severity": "high",     "severity_score": 6.8, "population_affected": 6400,  "vulnerability_index": 0.48, "source": "gdacs"},
    {"name": "Uttarakhand — Chamoli",     "state": "Uttarakhand", "district": "Chamoli",    "latitude": 30.4026,  "longitude": 79.3213,  "disaster_type": "landslide",  "severity": "medium",   "severity_score": 5.1, "population_affected": 3200,  "vulnerability_index": 0.40, "source": "ndma"},
    {"name": "Assam — Kamrup",            "state": "Assam",       "district": "Kamrup",     "latitude": 26.1433,  "longitude": 91.7362,  "disaster_type": "flood",      "severity": "medium",   "severity_score": 4.7, "population_affected": 4800,  "vulnerability_index": 0.42, "source": "gdacs"},
    {"name": "Bihar — Patna",             "state": "Bihar",       "district": "Patna",      "latitude": 25.5941,  "longitude": 85.1376,  "disaster_type": "flood",      "severity": "low",      "severity_score": 2.3, "population_affected": 1900,  "vulnerability_index": 0.30, "source": "ndma"},
    {"name": "Gujarat — Vadodara",        "state": "Gujarat",     "district": "Vadodara",   "latitude": 22.3072,  "longitude": 73.1812,  "disaster_type": "flood",      "severity": "low",      "severity_score": 1.8, "population_affected": 1200,  "vulnerability_index": 0.25, "source": "ndma"},
]

for z in zones_data:
    if not db.query(DisasterZone).filter(DisasterZone.name == z["name"]).first():
        db.add(DisasterZone(**z, is_active=1))

db.commit()

# ── RESOURCES ──────────────────────────────────────────────────────────────────
resources_data = [
    # Food & Water
    {"name": "Food Packets",    "category": "food",      "unit": "packets", "quantity_available": 42000, "quantity_total": 50000, "quantity_deployed": 8000,  "depot_id": delhi_depot.id  if delhi_depot  else None},
    {"name": "Water",           "category": "water",     "unit": "liters",  "quantity_available": 28000, "quantity_total": 40000, "quantity_deployed": 12000, "depot_id": mumbai_depot.id if mumbai_depot else None},
    {"name": "Water Purifiers", "category": "water",     "unit": "units",   "quantity_available": 12400, "quantity_total": 15000, "quantity_deployed": 2600,  "depot_id": delhi_depot.id  if delhi_depot  else None},
    # Medical
    {"name": "Medical Kits",    "category": "medical",   "unit": "kits",    "quantity_available": 8400,  "quantity_total": 12000, "quantity_deployed": 3600,  "depot_id": delhi_depot.id  if delhi_depot  else None, "critical_threshold": 0.30},
    {"name": "Medicine Stock",  "category": "medical",   "unit": "units",   "quantity_available": 14200, "quantity_total": 18000, "quantity_deployed": 3800,  "depot_id": mumbai_depot.id if mumbai_depot else None},
    {"name": "Blood Units",     "category": "medical",   "unit": "units",   "quantity_available": 1200,  "quantity_total": 1800,  "quantity_deployed": 600,   "depot_id": delhi_depot.id  if delhi_depot  else None, "critical_threshold": 0.35},
    # Transport
    {"name": "Rescue Vehicles", "category": "transport", "unit": "vehicles","quantity_available": 68,    "quantity_total": 80,    "quantity_deployed": 12,    "depot_id": delhi_depot.id  if delhi_depot  else None},
    {"name": "Helicopters",     "category": "transport", "unit": "units",   "quantity_available": 12,    "quantity_total": 18,    "quantity_deployed": 6,     "depot_id": delhi_depot.id  if delhi_depot  else None},
    # Shelter
    {"name": "Shelter Capacity","category": "shelter",   "unit": "persons", "quantity_available": 34000, "quantity_total": 42000, "quantity_deployed": 8000,  "depot_id": mumbai_depot.id if mumbai_depot else None},
]

for r in resources_data:
    if not db.query(Resource).filter(Resource.name == r["name"]).first():
        db.add(Resource(**r))

db.commit()

# ── FIELD TEAMS ────────────────────────────────────────────────────────────────
teams_data = [
    {"team_code": "Alpha-7", "team_name": "Alpha Response Team 7",  "members": 12, "status": "deployed", "location_txt": "Wayanad, Kerala"},
    {"team_code": "Beta-3",  "team_name": "Beta Response Team 3",   "members": 10, "status": "transit",  "location_txt": "En route -> Puri"},
    {"team_code": "Delta-2", "team_name": "Delta Response Team 2",  "members": 8,  "status": "deployed", "location_txt": "Chamoli, Uttarakhand"},
    {"team_code": "Gamma-1", "team_name": "Gamma Response Team 1",  "members": 15, "status": "standby",  "location_txt": "Hyderabad Base"},
    {"team_code": "Echo-5",  "team_name": "Echo Response Team 5",   "members": 11, "status": "deployed", "location_txt": "Idukki, Kerala"},
]

for t in teams_data:
    if not db.query(FieldTeam).filter(FieldTeam.team_code == t["team_code"]).first():
        db.add(FieldTeam(**t))

db.commit()
db.close()

print("[OK] Database seeded successfully!")
print(f"  Depots:    {len(depots_data)}")
print(f"  Zones:     {len(zones_data)}")
print(f"  Resources: {len(resources_data)}")
print(f"  Teams:     {len(teams_data)}")

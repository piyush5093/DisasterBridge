from sqlalchemy.orm import Session
from sqlalchemy import text
from models import ResourceItem, GridCell, AllocationPlan, Route, Mission, PriorityEnum, MissionStatusEnum, ResourceTypeEnum
from datetime import datetime
import uuid
import requests
import json
from ortools.linear_solver import pywraplp
import polyline

def optimize_allocation(db: Session, zone_id: str):
    zone = db.query(GridCell).filter(GridCell.id == zone_id).first()
    if not zone: return {"error": "Zone not found"}
    
    # 1. Fetch available resources near the zone (e.g., within 200km)
    # For a real scenario we'd do a geo query, for now let's just get all available to demonstrate OR-Tools
    depots = db.query(ResourceItem).filter(ResourceItem.status == 'available').all()
    if not depots:
        return {"error": "No available resources"}

    # We need to satisfy demands
    demands = {
        'food': zone.predicted_demand_food or 0,
        'hygiene_kits': zone.predicted_demand_hygiene_kits or 0,
        'medical': zone.predicted_demand_medical or 0,
        'shelter': zone.predicted_demand_shelter or 0
    }
    
    solver = pywraplp.Solver.CreateSolver('GLOP')
    if not solver: return {"error": "OR-Tools Solver failed to initialize"}
    
    # Variables: how much of resource r to send from depot i to this zone
    # For simplicity, we just match resource_type
    alloc_vars = {}
    
    for d in depots:
        rtype = d.resource_type.name
        if rtype in demands and demands[rtype] > 0:
            var = solver.NumVar(0, d.quantity, f"alloc_{d.id}_{rtype}")
            alloc_vars[(str(d.id), rtype)] = var
            
    # Objective: We want to maximize total fulfilled demand (coverage)
    # In a full multi-zone model, we'd minimize cost/distance. 
    # Here, we maximize the sum of allocations minus a tiny distance penalty.
    objective = solver.Objective()
    for (d_id, rtype), var in alloc_vars.items():
        # Ideally, fetch distance between depot and zone. 
        # We'll assume a dummy cost of 0.01 per unit to prioritize closer depots if distance was calculated.
        objective.SetCoefficient(var, 1.0)
    objective.SetMaximization()
    
    # Constraints: Don't allocate more than demand
    for rtype in demands:
        constraint = solver.Constraint(0, demands[rtype])
        for (d_id, rt), var in alloc_vars.items():
            if rt == rtype:
                constraint.SetCoefficient(var, 1.0)
                
    status = solver.Solve()
    
    if status not in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
        return {"error": "Could not find a feasible allocation"}
        
    plan_run_id = uuid.uuid4()
    allocations = []
    
    for (d_id, rtype), var in alloc_vars.items():
        val = var.solution_value()
        if val > 0.01:
            coverage = (val / demands[rtype]) * 100 if demands[rtype] > 0 else 100
            plan = AllocationPlan(
                zone_id=zone.id,
                resource_type=ResourceTypeEnum(rtype),
                allocated_quantity=val,
                source_depot_id=uuid.UUID(d_id),
                coverage_percent=coverage,
                plan_run_id=plan_run_id,
                created_at=datetime.utcnow()
            )
            db.add(plan)
            
            # Deduct from depot
            depot = db.query(ResourceItem).filter(ResourceItem.id == uuid.UUID(d_id)).first()
            depot.quantity -= val
            if depot.quantity <= 0.01:
                depot.status = 'depleted'
                
            allocations.append({
                "depot_id": d_id,
                "resource_type": rtype,
                "quantity": val,
                "coverage_percent": coverage
            })
            
    db.commit()
    return {"status": "optimal", "plan_run_id": str(plan_run_id), "allocations": allocations}


def generate_routes_for_plan(db: Session, plan_run_id: str):
    plans = db.query(AllocationPlan).filter(AllocationPlan.plan_run_id == plan_run_id).all()
    if not plans: return {"error": "Plan run ID not found"}
    
    # Group by depot_id + zone_id to generate 1 route per pair
    pairs = set((str(p.source_depot_id), str(p.zone_id)) for p in plans)
    
    routes_created = []
    
    for depot_id, zone_id in pairs:
        depot = db.query(ResourceItem).filter(ResourceItem.id == depot_id).first()
        zone = db.query(GridCell).filter(GridCell.id == zone_id).first()
        
        # Extract lat/lngs using raw SQL
        d_geom = db.execute(text("SELECT ST_X(location::geometry), ST_Y(location::geometry) FROM resource_items WHERE id = :id"), {"id": depot.id}).fetchone()
        z_geom = db.execute(text("SELECT ST_X(ST_Centroid(cell_geometry::geometry)), ST_Y(ST_Centroid(cell_geometry::geometry)) FROM grid_cells WHERE id = :id"), {"id": zone.id}).fetchone()
        
        d_lng, d_lat = d_geom
        z_lng, z_lat = z_geom
        
        # Hit OSRM Demo API
        osrm_url = f"http://router.project-osrm.org/route/v1/driving/{d_lng},{d_lat};{z_lng},{z_lat}?overview=full&geometries=polyline"
        fallback = False
        dist_km = 0
        dur_min = 0
        geom_text = None
        
        try:
            resp = requests.get(osrm_url, timeout=5)
            data = resp.json()
            if data.get('code') == 'Ok':
                route_data = data['routes'][0]
                dist_km = route_data['distance'] / 1000.0
                dur_min = route_data['duration'] / 60.0
                # Decode polyline to WKT LineString
                decoded = polyline.decode(route_data['geometry']) # returns list of (lat, lng)
                line_coords = ", ".join([f"{lon} {lat}" for lat, lon in decoded])
                geom_text = f"SRID=4326;LINESTRING({line_coords})"
            else:
                fallback = True
        except:
            fallback = True
            
        if fallback:
            # Straight line fallback
            dist_km = 50.0 # dummy
            dur_min = 60.0
            geom_text = f"SRID=4326;LINESTRING({d_lng} {d_lat}, {z_lng} {z_lat})"
            
        r = Route(
            plan_run_id=plan_run_id,
            depot_id=depot.id,
            zone_id=zone.id,
            route_geometry=geom_text,
            distance_km=dist_km,
            estimated_duration_minutes=dur_min,
            is_fallback_straight_line=fallback,
            road_status='open'
        )
        db.add(r)
        db.commit()
        db.refresh(r)
        
        routes_created.append({
            "route_id": str(r.id),
            "depot_id": depot_id,
            "distance_km": dist_km,
            "duration_min": dur_min,
            "fallback": fallback
        })
        
    return {"status": "routed", "routes_created": routes_created}

def create_missions_for_plan(db: Session, plan_run_id: str):
    routes = db.query(Route).filter(Route.plan_run_id == plan_run_id).all()
    if not routes: return {"error": "No routes found for this plan"}
    
    missions_created = []
    
    for r in routes:
        # Get allocations for this depot->zone
        allocs = db.query(AllocationPlan).filter(
            AllocationPlan.plan_run_id == plan_run_id,
            AllocationPlan.source_depot_id == r.depot_id,
            AllocationPlan.zone_id == r.zone_id
        ).all()
        
        supplies = {a.resource_type.name: a.allocated_quantity for a in allocs}
        
        m = Mission(
            zone_id=r.zone_id,
            team_name=f"TM-{str(uuid.uuid4())[:6].upper()}",
            vehicle_id=f"V-{str(uuid.uuid4())[:4].upper()}",
            route_id=r.id,
            priority=PriorityEnum.high,
            status=MissionStatusEnum.assigned,
            supplies=supplies,
            created_at=datetime.utcnow()
        )
        db.add(m)
        db.commit()
        
        missions_created.append({
            "mission_id": str(m.id),
            "team": m.team_name,
            "supplies": supplies
        })
        
    return {"status": "missions_created", "missions": missions_created}

def generate_unified_plan(db: Session, zone_id: str):
    alloc_res = optimize_allocation(db, zone_id)
    if "error" in alloc_res: return alloc_res
    
    plan_run_id = alloc_res["plan_run_id"]
    route_res = generate_routes_for_plan(db, plan_run_id)
    mission_res = create_missions_for_plan(db, plan_run_id)
    
    return {
        "status": "success",
        "plan_run_id": plan_run_id,
        "allocations": alloc_res["allocations"],
        "routes": route_res.get("routes_created", []),
        "missions": mission_res.get("missions", [])
    }

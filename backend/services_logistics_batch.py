from sqlalchemy.orm import Session
from sqlalchemy import text
from models import ResourceItem, GridCell, AllocationPlan, Route, Mission, PriorityEnum, MissionStatusEnum, ResourceTypeEnum
from datetime import datetime
import uuid
import requests
import json
from ortools.linear_solver import pywraplp
import polyline
import asyncio
import aiohttp

def optimize_allocation_batch(db: Session, zone_ids: list[str]):
    zones = db.query(GridCell).filter(GridCell.id.in_(zone_ids)).all()
    if not zones: return {"error": "Zones not found"}
    
    depots = db.query(ResourceItem).filter(ResourceItem.status == 'available').all()
    if not depots: return {"error": "No available resources"}

    solver = pywraplp.Solver.CreateSolver('GLOP')
    if not solver: return {"error": "OR-Tools Solver failed"}
    
    alloc_vars = {}
    
    # Track priority weights for the objective function
    prio_weights = {'low': 1.0, 'medium': 2.0, 'high': 5.0, 'critical': 10.0}
    
    for z in zones:
        # Priority 4: Use priority_override if present
        effective_prio = z.priority_override.name if z.priority_override else (z.priority.name if z.priority else 'low')
        weight = prio_weights.get(effective_prio, 1.0)
        
        demands = {
            'food': z.predicted_demand_food or 0,
            'hygiene_kits': z.predicted_demand_hygiene_kits or 0,
            'medical': z.predicted_demand_medical or 0,
            'shelter': z.predicted_demand_shelter or 0
        }
        
        for d in depots:
            rtype = d.resource_type.name
            if rtype in demands and demands[rtype] > 0:
                # Variable: amount of resource rtype from depot d to zone z
                var = solver.NumVar(0, min(d.quantity, demands[rtype]), f"alloc_{d.id}_{z.id}_{rtype}")
                alloc_vars[(str(d.id), str(z.id), rtype)] = var
                
    # Constraints: 
    # 1. Depot limits (sum of out-allocations from depot <= depot.quantity)
    for d in depots:
        rtype = d.resource_type.name
        constraint = solver.Constraint(0, d.quantity)
        for (d_id, z_id, rt), var in alloc_vars.items():
            if d_id == str(d.id):
                constraint.SetCoefficient(var, 1.0)
                
    # 2. Zone demand limits (sum of in-allocations to zone <= zone.demand)
    for z in zones:
        demands = {
            'food': z.predicted_demand_food or 0,
            'hygiene_kits': z.predicted_demand_hygiene_kits or 0,
            'medical': z.predicted_demand_medical or 0,
            'shelter': z.predicted_demand_shelter or 0
        }
        for rt, dem in demands.items():
            constraint = solver.Constraint(0, dem)
            for (d_id, z_id, rtype), var in alloc_vars.items():
                if z_id == str(z.id) and rtype == rt:
                    constraint.SetCoefficient(var, 1.0)
    
    # Objective: Maximize coverage weighted by zone priority
    objective = solver.Objective()
    for (d_id, z_id, rtype), var in alloc_vars.items():
        z = next(zone for zone in zones if str(zone.id) == z_id)
        effective_prio = z.priority_override.name if z.priority_override else (z.priority.name if z.priority else 'low')
        weight = prio_weights.get(effective_prio, 1.0)
        objective.SetCoefficient(var, weight)
        
    objective.SetMaximization()
    status = solver.Solve()
    
    if status not in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
        return {"error": "Could not find a feasible allocation"}
        
    plan_run_id = uuid.uuid4()
    allocations = []
    
    for (d_id, z_id, rtype), var in alloc_vars.items():
        val = var.solution_value()
        if val > 0.01:
            z = next(zone for zone in zones if str(zone.id) == z_id)
            dem = getattr(z, f'predicted_demand_{rtype}') or 0
            coverage = (val / dem) * 100 if dem > 0 else 100
            plan = AllocationPlan(
                zone_id=uuid.UUID(z_id),
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
                "zone_id": z_id,
                "resource_type": rtype,
                "quantity": val,
                "coverage_percent": coverage
            })
            
    db.commit()
    return {"status": "optimal", "plan_run_id": str(plan_run_id), "allocations": allocations}


async def fetch_route(session, depot_id, zone_id, d_lng, d_lat, z_lng, z_lat, semaphore):
    async with semaphore:
        osrm_url = f"http://router.project-osrm.org/route/v1/driving/{d_lng},{d_lat};{z_lng},{z_lat}?overview=full&geometries=polyline"
        try:
            async with session.get(osrm_url, timeout=5) as resp:
                data = await resp.json()
                if data.get('code') == 'Ok':
                    route_data = data['routes'][0]
                    dist_km = route_data['distance'] / 1000.0
                    dur_min = route_data['duration'] / 60.0
                    decoded = polyline.decode(route_data['geometry']) 
                    line_coords = ", ".join([f"{lon} {lat}" for lat, lon in decoded])
                    geom_text = f"SRID=4326;LINESTRING({line_coords})"
                    return depot_id, zone_id, geom_text, dist_km, dur_min, False
        except:
            pass
            
        # Fallback
        return depot_id, zone_id, f"SRID=4326;LINESTRING({d_lng} {d_lat}, {z_lng} {z_lat})", 50.0, 60.0, True

async def generate_routes_for_plan_async(db: Session, plan_run_id: str):
    plans = db.query(AllocationPlan).filter(AllocationPlan.plan_run_id == plan_run_id).all()
    if not plans: return {"error": "Plan run ID not found"}
    
    pairs = set((str(p.source_depot_id), str(p.zone_id)) for p in plans)
    
    # Pre-fetch geometries to avoid synchronous DB queries inside asyncio loop
    coords = {}
    for depot_id, zone_id in pairs:
        d_geom = db.execute(text("SELECT ST_X(location::geometry), ST_Y(location::geometry) FROM resource_items WHERE id = :id"), {"id": depot_id}).fetchone()
        z_geom = db.execute(text("SELECT ST_X(ST_Centroid(cell_geometry::geometry)), ST_Y(ST_Centroid(cell_geometry::geometry)) FROM grid_cells WHERE id = :id"), {"id": zone_id}).fetchone()
        coords[(depot_id, zone_id)] = (d_geom[0], d_geom[1], z_geom[0], z_geom[1])
        
    semaphore = asyncio.Semaphore(5)
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for (depot_id, zone_id), (d_lng, d_lat, z_lng, z_lat) in coords.items():
            tasks.append(fetch_route(session, depot_id, zone_id, d_lng, d_lat, z_lng, z_lat, semaphore))
            
        results = await asyncio.gather(*tasks)
        
    routes_created = []
    for depot_id, zone_id, geom_text, dist_km, dur_min, fallback in results:
        r = Route(
            plan_run_id=plan_run_id,
            depot_id=uuid.UUID(depot_id),
            zone_id=uuid.UUID(zone_id),
            route_geometry=geom_text,
            distance_km=dist_km,
            estimated_duration_minutes=dur_min,
            is_fallback_straight_line=fallback,
            road_status='open'
        )
        db.add(r)
        
    db.commit()
    
    # Query back to return objects
    saved = db.query(Route).filter(Route.plan_run_id == plan_run_id).all()
    for s in saved:
        routes_created.append({
            "route_id": str(s.id),
            "depot_id": str(s.depot_id),
            "zone_id": str(s.zone_id),
            "distance_km": s.distance_km,
            "duration_min": s.estimated_duration_minutes,
            "fallback": s.is_fallback_straight_line
        })
        
    return {"status": "routed", "routes_created": routes_created}

def generate_unified_plan_batch(db: Session, zone_ids: list[str], create_missions: bool = True):
    alloc_res = optimize_allocation_batch(db, zone_ids)
    if "error" in alloc_res: return alloc_res
    
    plan_run_id = alloc_res["plan_run_id"]
    
    # Run async routes loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    route_res = loop.run_until_complete(generate_routes_for_plan_async(db, plan_run_id))
    
    mission_res = {"missions": []}
    if create_missions:
        from services_logistics import create_missions_for_plan
        mission_res = create_missions_for_plan(db, plan_run_id)
        
    return {
        "status": "success",
        "plan_run_id": plan_run_id,
        "allocations": alloc_res["allocations"],
        "routes": route_res.get("routes_created", []),
        "missions": mission_res.get("missions", [])
    }

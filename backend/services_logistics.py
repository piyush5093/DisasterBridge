from sqlalchemy.orm import Session
from sqlalchemy import text
from models import ResourceItem, GridCell, AllocationPlan, Route, Mission, PriorityEnum, MissionStatusEnum, ResourceTypeEnum
from datetime import datetime
import uuid, math, requests, json
from ortools.linear_solver import pywraplp
import polyline


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return straight-line distance in km between two lat/lng points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def optimize_allocation(db: Session, zone_id: str):
    zone = db.query(GridCell).filter(GridCell.id == zone_id).first()
    if not zone:
        return {"error": "Zone not found"}

    # Get zone centroid coordinates
    z_row = db.execute(
        text("SELECT ST_X(ST_Centroid(cell_geometry::geometry)), ST_Y(ST_Centroid(cell_geometry::geometry)) FROM grid_cells WHERE id = :id"),
        {"id": zone_id}
    ).fetchone()
    if not z_row:
        return {"error": "Zone geometry not found"}
    z_lng, z_lat = float(z_row[0]), float(z_row[1])

    # Fetch all available depots WITH their coordinates and compute distance
    raw_depots = db.execute(text("""
        SELECT id, resource_type, quantity, depot_name,
               ST_X(location::geometry) AS lng,
               ST_Y(location::geometry) AS lat
        FROM resource_items
        WHERE status = 'available' AND quantity > 0
        ORDER BY ST_Distance(
            location::geometry::geography,
            ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
        ) ASC
    """), {"lng": z_lng, "lat": z_lat}).fetchall()

    if not raw_depots:
        return {"error": "No available resources"}

    # Build enriched depot list with real km distances
    depots = []
    for row in raw_depots:
        d_lng, d_lat = float(row[4]), float(row[5])
        dist_km = _haversine_km(z_lat, z_lng, d_lat, d_lng)
        depots.append({
            "id": str(row[0]),
            "resource_type": row[1].name if hasattr(row[1], "name") else str(row[1]),
            "quantity": float(row[2]),
            "depot_name": row[3],
            "lat": d_lat,
            "lng": d_lng,
            "dist_km": dist_km,
        })

    demands = {
        'food':         zone.predicted_demand_food or 0,
        'hygiene_kits': zone.predicted_demand_hygiene_kits or 0,
        'medical':      zone.predicted_demand_medical or 0,
        'shelter':      zone.predicted_demand_shelter or 0,
    }

    solver = pywraplp.Solver.CreateSolver('GLOP')
    if not solver:
        return {"error": "OR-Tools Solver failed to initialize"}

    # Variables: how much of resource r to send from depot d
    alloc_vars = {}
    for d in depots:
        rtype = d["resource_type"]
        if rtype in demands and demands[rtype] > 0:
            var = solver.NumVar(0, d["quantity"], f"alloc_{d['id']}_{rtype}")
            alloc_vars[(d["id"], rtype)] = (var, d["dist_km"])

    if not alloc_vars:
        return {"error": "No matching resource types available for this zone's demand"}

    # --- DISTANCE-AWARE OBJECTIVE ---
    # Maximize coverage (1 unit = +1) but penalize distance:
    # Score = 1.0 - (dist_km / max_dist) * 0.5
    # This means a depot 0 km away scores 1.0, one 1000 km away scores 0.5
    # So closer depots are always preferred first.
    max_dist = max(d_km for _, (_, d_km) in alloc_vars.items()) if alloc_vars else 1.0
    max_dist = max(max_dist, 1.0)  # avoid division by zero

    objective = solver.Objective()
    for (d_id, rtype), (var, dist_km) in alloc_vars.items():
        # Proximity score: 1.0 at 0 km, approaches 0.5 at max_dist
        proximity_score = 1.0 - (dist_km / max_dist) * 0.5
        objective.SetCoefficient(var, proximity_score)
    objective.SetMaximization()

    # Constraints: don't exceed demand per resource type
    for rtype in demands:
        if demands[rtype] > 0:
            constraint = solver.Constraint(0, demands[rtype])
            for (d_id, rt), (var, _) in alloc_vars.items():
                if rt == rtype:
                    constraint.SetCoefficient(var, 1.0)

    status = solver.Solve()
    if status not in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
        return {"error": "Could not find a feasible allocation"}

    plan_run_id = uuid.uuid4()
    allocations = []

    for (d_id, rtype), (var, dist_km) in alloc_vars.items():
        val = var.solution_value()
        if val > 0.01:
            coverage = (val / demands[rtype]) * 100 if demands[rtype] > 0 else 100
            depot_info = next(d for d in depots if d["id"] == d_id)

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
            depot_obj = db.query(ResourceItem).filter(ResourceItem.id == uuid.UUID(d_id)).first()
            if depot_obj:
                depot_obj.quantity -= val
                if depot_obj.quantity <= 0.01:
                    depot_obj.status = 'depleted'

            allocations.append({
                "depot_id": d_id,
                "depot_name": depot_info["depot_name"],
                "resource_type": rtype,
                "quantity": val,
                "coverage_percent": coverage,
                "distance_km": round(dist_km, 1),
            })

    db.commit()

    # Sort result by distance so response shows nearest-first
    allocations.sort(key=lambda x: x["distance_km"])

    return {
        "status": "optimal",
        "plan_run_id": str(plan_run_id),
        "zone_lat": z_lat,
        "zone_lng": z_lng,
        "allocations": allocations,
    }


def generate_routes_for_plan(db: Session, plan_run_id: str):
    plans = db.query(AllocationPlan).filter(AllocationPlan.plan_run_id == plan_run_id).all()
    if not plans:
        return {"error": "Plan run ID not found"}

    # Group by depot_id + zone_id to generate 1 route per pair
    pairs = set((str(p.source_depot_id), str(p.zone_id)) for p in plans)
    routes_created = []

    for depot_id, zone_id in pairs:
        depot = db.query(ResourceItem).filter(ResourceItem.id == depot_id).first()
        zone  = db.query(GridCell).filter(GridCell.id == zone_id).first()

        d_geom = db.execute(text("SELECT ST_X(location::geometry), ST_Y(location::geometry) FROM resource_items WHERE id = :id"), {"id": depot.id}).fetchone()
        z_geom = db.execute(text("SELECT ST_X(ST_Centroid(cell_geometry::geometry)), ST_Y(ST_Centroid(cell_geometry::geometry)) FROM grid_cells WHERE id = :id"), {"id": zone.id}).fetchone()

        d_lng, d_lat = float(d_geom[0]), float(d_geom[1])
        z_lng, z_lat = float(z_geom[0]), float(z_geom[1])

        # Hit OSRM Demo API
        osrm_url = f"http://router.project-osrm.org/route/v1/driving/{d_lng},{d_lat};{z_lng},{z_lat}?overview=full&geometries=polyline"
        fallback = False
        dist_km  = 0
        dur_min  = 0
        geom_text = None

        try:
            resp = requests.get(osrm_url, timeout=5)
            data = resp.json()
            if data.get('code') == 'Ok':
                route_data = data['routes'][0]
                dist_km   = route_data['distance'] / 1000.0
                dur_min   = route_data['duration'] / 60.0
                decoded   = polyline.decode(route_data['geometry'])
                line_coords = ", ".join([f"{lon} {lat}" for lat, lon in decoded])
                geom_text = f"SRID=4326;LINESTRING({line_coords})"
            else:
                fallback = True
        except Exception:
            fallback = True

        if fallback:
            # Haversine straight-line as fallback
            dist_km   = round(_haversine_km(d_lat, d_lng, z_lat, z_lng), 1)
            dur_min   = dist_km / 60.0 * 60  # assume 60 km/h avg
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
            "route_id":    str(r.id),
            "depot_id":    depot_id,
            "distance_km": dist_km,
            "duration_min": dur_min,
            "fallback":    fallback,
        })

    return {"status": "routed", "routes_created": routes_created}


def create_missions_for_plan(db: Session, plan_run_id: str):
    routes = db.query(Route).filter(Route.plan_run_id == plan_run_id).all()
    if not routes:
        return {"error": "No routes found for this plan"}

    missions_created = []
    for r in routes:
        allocs = db.query(AllocationPlan).filter(
            AllocationPlan.plan_run_id == plan_run_id,
            AllocationPlan.source_depot_id == r.depot_id,
            AllocationPlan.zone_id == r.zone_id,
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
            "supplies": supplies,
        })

    return {"status": "missions_created", "missions": missions_created}


def generate_unified_plan(db: Session, zone_id: str):
    alloc_res = optimize_allocation(db, zone_id)
    if "error" in alloc_res:
        return alloc_res

    plan_run_id = alloc_res["plan_run_id"]
    route_res   = generate_routes_for_plan(db, plan_run_id)
    mission_res = create_missions_for_plan(db, plan_run_id)

    return {
        "status":      "success",
        "plan_run_id": plan_run_id,
        "allocations": alloc_res["allocations"],
        "routes":      route_res.get("routes_created", []),
        "missions":    mission_res.get("missions", []),
    }

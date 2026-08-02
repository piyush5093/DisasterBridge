"""
Resource Optimizer Service
==========================
Greedy allocation engine that assigns resources from depots to disaster zones.

Algorithm:
1. For each zone (sorted by severity score desc), find the nearest active depot
   that has sufficient available resources.
2. Calculate estimated delivery time using Haversine distance + avg truck speed (60 km/h).
3. Return a structured allocation plan.

Usage:
    from app.services.resource_optimizer import optimizer
    plan = optimizer.allocate(zone, depots, resources)
"""

import math
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Haversine distance (km) between two lat/lon points
# ---------------------------------------------------------------------------
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance in km between two geo points."""
    R = 6371.0  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class AllocationItem:
    resource_id: int
    resource_name: str
    category: str
    quantity_dispatched: int
    unit: str


@dataclass
class AllocationPlan:
    zone_id: int
    zone_name: str
    severity: str
    severity_score: float
    depot_id: int
    depot_name: str
    distance_km: float
    estimated_hours: float
    priority: str                           # "critical" / "high" / "medium" / "low"
    resources: List[AllocationItem] = field(default_factory=list)
    warnings: List[str]            = field(default_factory=list)
    feasible: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "zone_id":          self.zone_id,
            "zone_name":        self.zone_name,
            "severity":         self.severity,
            "severity_score":   self.severity_score,
            "depot_id":         self.depot_id,
            "depot_name":       self.depot_name,
            "distance_km":      round(self.distance_km, 2),
            "estimated_hours":  round(self.estimated_hours, 2),
            "priority":         self.priority,
            "feasible":         self.feasible,
            "resources":        [
                {
                    "resource_id":          r.resource_id,
                    "resource_name":        r.resource_name,
                    "category":             r.category,
                    "quantity_dispatched":  r.quantity_dispatched,
                    "unit":                 r.unit,
                }
                for r in self.resources
            ],
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# Resource demand requirements per severity level (per 1000 affected people)
# ---------------------------------------------------------------------------
DEMAND_PER_1K = {
    "critical": {"food": 3000, "water": 5000, "medical": 150, "shelter": 600, "transport": 5},
    "high":     {"food": 2000, "water": 3500, "medical": 100, "shelter": 400, "transport": 3},
    "medium":   {"food": 1200, "water": 2000, "medical": 60,  "shelter": 250, "transport": 2},
    "low":      {"food": 600,  "water": 1000, "medical": 30,  "shelter": 100, "transport": 1},
}

AVG_TRUCK_SPEED_KPH = 60.0


# ---------------------------------------------------------------------------
# Optimizer class
# ---------------------------------------------------------------------------
class ResourceOptimizer:
    """
    Greedy priority-based resource allocator.
    Zones are sorted by severity (critical first), then assigned to
    the nearest depot that can satisfy at least 50% of required demand.
    """

    def allocate_single_zone(
        self,
        zone,
        depots: list,
        resources: list,
    ) -> AllocationPlan:
        """
        Generate an allocation plan for one DisasterZone.

        Args:
            zone:      DisasterZone ORM object
            depots:    List of Depot ORM objects (active)
            resources: List of Resource ORM objects (all)

        Returns:
            AllocationPlan dataclass
        """
        warnings: List[str] = []

        # ── 1. Find nearest depot ────────────────────────────────────────────
        if not depots:
            return AllocationPlan(
                zone_id=zone.id, zone_name=zone.name,
                severity=zone.severity, severity_score=zone.severity_score,
                depot_id=-1, depot_name="N/A",
                distance_km=0, estimated_hours=0,
                priority=zone.severity,
                feasible=False,
                warnings=["No active depots available"],
            )

        # Sort depots by distance to zone
        depots_sorted = sorted(
            depots,
            key=lambda d: haversine_km(zone.latitude, zone.longitude, d.latitude, d.longitude)
        )
        nearest_depot = depots_sorted[0]
        dist_km = haversine_km(
            zone.latitude, zone.longitude,
            nearest_depot.latitude, nearest_depot.longitude
        )
        est_hours = dist_km / AVG_TRUCK_SPEED_KPH

        # ── 2. Calculate required demand ─────────────────────────────────────
        pop = max(zone.population_affected or 0, 100)
        severity = (zone.severity or "medium").lower()
        demand_per_1k = DEMAND_PER_1K.get(severity, DEMAND_PER_1K["medium"])

        required: Dict[str, int] = {
            cat: max(1, int(qty * pop / 1000))
            for cat, qty in demand_per_1k.items()
        }

        # ── 3. Match available resources from nearest depot ──────────────────
        depot_resources = [r for r in resources if r.depot_id == nearest_depot.id]
        if not depot_resources:
            # Use any available resources if depot has none assigned
            depot_resources = [r for r in resources if r.quantity_available > 0]
            if depot_resources:
                warnings.append(
                    f"Depot '{nearest_depot.name}' has no assigned resources. "
                    "Using unassigned available stock."
                )

        # Category map from depot resources
        cat_map: Dict[str, list] = {}
        for r in depot_resources:
            # Normalise category aliases: transport→transport, shelter→shelter
            cat = r.category.lower()
            cat_map.setdefault(cat, []).append(r)

        allocation_items: List[AllocationItem] = []
        unmet: List[str] = []

        CAT_ALIASES = {
            "food": ["food"],
            "water": ["water"],
            "medical": ["medical"],
            "shelter": ["shelter"],
            "transport": ["transport", "vehicles"],
        }

        for need_cat, need_qty in required.items():
            aliases = CAT_ALIASES.get(need_cat, [need_cat])
            matched_resources = []
            for alias in aliases:
                matched_resources.extend(cat_map.get(alias, []))

            if not matched_resources:
                unmet.append(need_cat)
                continue

            remaining = need_qty
            for res in matched_resources:
                if remaining <= 0:
                    break
                dispatch = min(res.quantity_available, remaining)
                if dispatch > 0:
                    allocation_items.append(AllocationItem(
                        resource_id=res.id,
                        resource_name=res.name,
                        category=res.category,
                        quantity_dispatched=dispatch,
                        unit=res.unit,
                    ))
                    remaining -= dispatch

            if remaining > 0:
                coverage = round((need_qty - remaining) / need_qty * 100, 1)
                warnings.append(
                    f"{need_cat.title()}: only {coverage}% of demand can be met "
                    f"({need_qty - remaining}/{need_qty} {matched_resources[0].unit if matched_resources else 'units'})"
                )

        if unmet:
            warnings.append(f"No resources available for categories: {', '.join(unmet)}")

        feasible = len(allocation_items) > 0

        return AllocationPlan(
            zone_id=zone.id,
            zone_name=zone.name,
            severity=zone.severity,
            severity_score=zone.severity_score,
            depot_id=nearest_depot.id,
            depot_name=nearest_depot.name,
            distance_km=dist_km,
            estimated_hours=est_hours,
            priority=severity,
            resources=allocation_items,
            warnings=warnings,
            feasible=feasible,
        )

    def allocate_all_zones(
        self,
        zones: list,
        depots: list,
        resources: list,
    ) -> List[AllocationPlan]:
        """
        Generate allocation plans for multiple zones (sorted by severity score).
        """
        # Sort zones: critical first, then by severity_score desc
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_zones = sorted(
            zones,
            key=lambda z: (severity_order.get((z.severity or "low").lower(), 4), -z.severity_score)
        )

        plans: List[AllocationPlan] = []
        for zone in sorted_zones:
            plan = self.allocate_single_zone(zone, depots, resources)
            plans.append(plan)

        return plans

    def get_optimal_routing(
        self,
        zone_id: int,
        depot_id: int,
        depots: list,
        zones: list,
    ) -> Dict[str, Any]:
        """
        Generate point-to-point routing info between a depot and a zone.
        Uses Haversine for straight-line distance; real routing requires
        a mapping API (Google Maps / OSRM) in production.
        """
        zone = next((z for z in zones if z.id == zone_id), None)
        depot = next((d for d in depots if d.id == depot_id), None)

        if not zone or not depot:
            return {"error": "Zone or Depot not found", "feasible": False}

        dist_km = haversine_km(
            depot.latitude, depot.longitude,
            zone.latitude, zone.longitude
        )
        est_hours = dist_km / AVG_TRUCK_SPEED_KPH

        return {
            "zone_id":   zone.id,
            "zone_name": zone.name,
            "depot_id":  depot.id,
            "depot_name": depot.name,
            "origin":    {"lat": depot.latitude, "lon": depot.longitude, "name": depot.city},
            "destination": {"lat": zone.latitude, "lon": zone.longitude, "name": zone.name},
            "distance_km":     round(dist_km, 2),
            "estimated_hours": round(est_hours, 2),
            "routing_method":  "haversine_straight_line",
            "note": "For road-accurate routing, integrate OSRM or Google Maps Directions API.",
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
optimizer = ResourceOptimizer()

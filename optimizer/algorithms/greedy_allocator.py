"""
Greedy Resource Allocator
=========================
Pure-Python greedy allocator (no heavy deps) for resource allocation.
This module can be imported standalone (no FastAPI/SQLAlchemy needed).

Usage:
    from optimizer.algorithms.greedy_allocator import GreedyAllocator, haversine_km

    result = GreedyAllocator.allocate(
        zone={"id": 1, "name": "Kerala Zone", "lat": 10.5, "lon": 76.2,
              "severity": "critical", "population_affected": 15000},
        depots=[{"id": 1, "name": "Depot HQ", "lat": 11.0, "lon": 76.9}],
        inventory={"food": 5000, "water": 8000, "medical": 300},
    )
"""

import math
from typing import List, Dict, Any, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TRUCK_SPEED_KPH = 60.0
EARTH_RADIUS_KM = 6371.0

DEMAND_SCALES = {
    "critical": 1.50,
    "high":     1.20,
    "medium":   1.00,
    "low":      0.70,
}

# Per 1000 affected persons per 3-day supply window
BASE_DEMAND_PER_1K = {
    "food":      3000,   # packets
    "water":     5000,   # liters
    "medical":   150,    # kits
    "shelter":   600,    # capacity slots
    "transport": 5,      # vehicles
}


# ---------------------------------------------------------------------------
# Haversine
# ---------------------------------------------------------------------------
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return EARTH_RADIUS_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def eta_hours(dist_km: float, speed_kph: float = TRUCK_SPEED_KPH) -> float:
    """Estimated travel hours given distance and speed."""
    return dist_km / speed_kph if speed_kph > 0 else 0.0


# ---------------------------------------------------------------------------
# Demand calculator
# ---------------------------------------------------------------------------
def calculate_demand(
    population: int,
    severity: str,
    categories: Optional[List[str]] = None,
) -> Dict[str, int]:
    """
    Calculate resource demand for a population given disaster severity.

    Args:
        population: Number of affected people
        severity:   'critical' | 'high' | 'medium' | 'low'
        categories: Optional list of specific categories to calculate

    Returns:
        Dict mapping category → required quantity
    """
    scale = DEMAND_SCALES.get(severity.lower(), 1.0)
    pop_k = max(population, 100) / 1000.0

    categories = categories or list(BASE_DEMAND_PER_1K.keys())
    return {
        cat: max(1, int(BASE_DEMAND_PER_1K[cat] * pop_k * scale))
        for cat in categories
        if cat in BASE_DEMAND_PER_1K
    }


# ---------------------------------------------------------------------------
# Greedy Allocator
# ---------------------------------------------------------------------------
class GreedyAllocator:
    """
    Stateless greedy allocator.
    All methods are classmethods — instantiation not required.
    """

    @classmethod
    def find_nearest_depot(
        cls,
        zone_lat: float,
        zone_lon: float,
        depots: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Return the nearest depot dict to the given coordinates."""
        if not depots:
            return None
        return min(
            depots,
            key=lambda d: haversine_km(zone_lat, zone_lon, d["lat"], d["lon"])
        )

    @classmethod
    def allocate(
        cls,
        zone: Dict[str, Any],
        depots: List[Dict[str, Any]],
        inventory: Dict[str, int],
    ) -> Dict[str, Any]:
        """
        Greedy allocation for a single zone.

        Args:
            zone: {"id", "name", "lat", "lon", "severity", "population_affected"}
            depots: [{"id", "name", "lat", "lon"}, ...]
            inventory: {"food": 5000, "water": 8000, ...} total available stock

        Returns:
            Allocation result dict
        """
        warnings: List[str] = []
        zone_lat = zone.get("lat") or zone.get("latitude", 0)
        zone_lon = zone.get("lon") or zone.get("longitude", 0)
        severity = zone.get("severity", "medium").lower()
        population = zone.get("population_affected", 1000)

        nearest = cls.find_nearest_depot(zone_lat, zone_lon, depots)
        if not nearest:
            return {
                "feasible": False,
                "zone_id": zone.get("id"),
                "warnings": ["No depots available"],
            }

        dist = haversine_km(zone_lat, zone_lon, nearest["lat"], nearest["lon"])
        eta  = eta_hours(dist)

        required = calculate_demand(population, severity)

        dispatched: Dict[str, int] = {}
        unmet: List[str] = []

        for cat, needed in required.items():
            available = inventory.get(cat, 0)
            give = min(available, needed)
            dispatched[cat] = give
            if give < needed:
                pct = round(give / needed * 100, 1) if needed > 0 else 0
                warnings.append(f"{cat}: only {pct}% demand met ({give}/{needed})")
                if give == 0:
                    unmet.append(cat)

        if unmet:
            warnings.append(f"Completely unmet categories: {', '.join(unmet)}")

        return {
            "feasible":        True,
            "zone_id":         zone.get("id"),
            "zone_name":       zone.get("name"),
            "severity":        severity,
            "population":      population,
            "depot_id":        nearest.get("id"),
            "depot_name":      nearest.get("name"),
            "distance_km":     round(dist, 2),
            "estimated_hours": round(eta, 2),
            "required":        required,
            "dispatched":      dispatched,
            "warnings":        warnings,
        }

    @classmethod
    def allocate_batch(
        cls,
        zones: List[Dict[str, Any]],
        depots: List[Dict[str, Any]],
        inventory: Dict[str, int],
    ) -> List[Dict[str, Any]]:
        """
        Allocate resources for multiple zones.
        Processes in priority order: critical → high → medium → low.
        Remaining inventory is decremented after each allocation.
        """
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_zones = sorted(
            zones,
            key=lambda z: severity_order.get(z.get("severity", "low").lower(), 4)
        )

        remaining_inventory = dict(inventory)
        results = []

        for zone in sorted_zones:
            result = cls.allocate(zone, depots, remaining_inventory)

            # Deduct dispatched from remaining inventory
            if result.get("feasible") and result.get("dispatched"):
                for cat, qty in result["dispatched"].items():
                    remaining_inventory[cat] = max(0, remaining_inventory.get(cat, 0) - qty)

            results.append(result)

        return results


# ---------------------------------------------------------------------------
# Standalone CLI test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sample_zones = [
        {"id": 1, "name": "Kerala — Wayanad", "lat": 11.69, "lon": 76.13,
         "severity": "critical", "population_affected": 18200},
        {"id": 2, "name": "Odisha — Puri",    "lat": 19.81, "lon": 85.83,
         "severity": "high",     "population_affected": 9500},
    ]
    sample_depots = [
        {"id": 1, "name": "Chennai Depot",   "lat": 13.08, "lon": 80.27},
        {"id": 2, "name": "Hyderabad Depot", "lat": 17.38, "lon": 78.47},
        {"id": 3, "name": "Kolkata Depot",   "lat": 22.57, "lon": 88.36},
    ]
    sample_inventory = {
        "food": 100000, "water": 200000,
        "medical": 5000, "shelter": 30000, "transport": 200
    }

    plans = GreedyAllocator.allocate_batch(sample_zones, sample_depots, sample_inventory)
    for p in plans:
        print(f"\n=== {p['zone_name']} ({p['severity'].upper()}) ===")
        print(f"  Depot    : {p['depot_name']} ({p['distance_km']} km, ETA {p['estimated_hours']}h)")
        print(f"  Dispatch : {p['dispatched']}")
        if p["warnings"]:
            print(f"  Warnings : {p['warnings']}")

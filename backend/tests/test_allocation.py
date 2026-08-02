import sys
import os
import pytest

# Add backend root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
# Add project root (parent of backend) to find optimizer package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from optimizer.algorithms.greedy_allocator import (
    GreedyAllocator,
    haversine_km,
    calculate_demand,
    DEMAND_SCALES,
)


# ---------------------------------------------------------------------------
# Unit tests for the greedy allocator (no FastAPI/DB needed)
# ---------------------------------------------------------------------------
class TestGreedyAllocatorUnit:

    def test_haversine_same_point(self):
        """Distance between same point should be 0."""
        dist = haversine_km(13.0, 80.0, 13.0, 80.0)
        assert dist == pytest.approx(0.0, abs=0.01)

    def test_haversine_known_distance(self):
        """Chennai to Mumbai is roughly 1030 km."""
        # Chennai: 13.08, 80.27  |  Mumbai: 19.07, 72.88
        dist = haversine_km(13.08, 80.27, 19.07, 72.88)
        assert 950 < dist < 1100, f"Expected ~1030 km, got {dist:.1f}"

    def test_calculate_demand_scales_with_severity(self):
        """Critical demand should be higher than low for same population."""
        d_critical = calculate_demand(10000, "critical")
        d_low      = calculate_demand(10000, "low")
        assert d_critical["food"] > d_low["food"]
        assert d_critical["water"] > d_low["water"]

    def test_calculate_demand_scales_with_population(self):
        """Demand should scale linearly with population."""
        d_small = calculate_demand(1000, "high")
        d_large = calculate_demand(10000, "high")
        # 10x population → ~10x demand
        ratio = d_large["food"] / d_small["food"]
        assert 8.0 < ratio < 12.0, f"Expected ~10x ratio, got {ratio:.2f}"

    def test_allocate_single_zone_basic(self):
        """Greedy allocator should return a feasible plan when inventory is available."""
        zone = {
            "id": 1, "name": "Test Zone",
            "lat": 13.08, "lon": 80.27,
            "severity": "high", "population_affected": 5000
        }
        depots = [
            {"id": 1, "name": "Chennai Depot", "lat": 13.08, "lon": 80.27},
        ]
        inventory = {
            "food": 100000, "water": 200000,
            "medical": 5000, "shelter": 10000, "transport": 50
        }

        result = GreedyAllocator.allocate(zone, depots, inventory)

        assert result["feasible"] is True
        assert result["zone_id"] == 1
        assert result["depot_id"] == 1
        assert result["distance_km"] == pytest.approx(0.0, abs=1.0)
        assert result["dispatched"]["food"] > 0
        assert result["dispatched"]["water"] > 0

    def test_allocate_no_depots(self):
        """Allocator should return infeasible when no depots available."""
        zone = {"id": 1, "name": "Zone", "lat": 13.0, "lon": 80.0,
                "severity": "critical", "population_affected": 10000}
        result = GreedyAllocator.allocate(zone, [], {"food": 100})
        assert result["feasible"] is False
        assert len(result["warnings"]) > 0

    def test_allocate_insufficient_inventory(self):
        """Allocator should still be feasible but issue warnings on partial fulfillment."""
        zone = {
            "id": 1, "name": "Zone",
            "lat": 13.0, "lon": 80.0,
            "severity": "critical", "population_affected": 50000
        }
        depots = [{"id": 1, "name": "Small Depot", "lat": 13.0, "lon": 80.0}]
        inventory = {"food": 100, "water": 100}  # Far less than needed

        result = GreedyAllocator.allocate(zone, depots, inventory)
        # Should be feasible but with warnings
        assert result["feasible"] is True
        assert len(result["warnings"]) > 0
        # Dispatched should not exceed available
        assert result["dispatched"]["food"] <= 100

    def test_allocate_nearest_depot_selected(self):
        """Allocator should select the geographically nearest depot."""
        zone = {"id": 1, "name": "Odisha Zone", "lat": 20.0, "lon": 86.0,
                "severity": "high", "population_affected": 5000}
        depots = [
            {"id": 1, "name": "Mumbai Depot",  "lat": 19.0, "lon": 72.8},   # far
            {"id": 2, "name": "Kolkata Depot", "lat": 22.5, "lon": 88.3},   # closer
            {"id": 3, "name": "Bhubaneswar",   "lat": 20.3, "lon": 85.8},   # nearest
        ]
        inventory = {"food": 10000, "water": 20000, "medical": 500}
        result = GreedyAllocator.allocate(zone, depots, inventory)
        assert result["depot_id"] == 3, "Should select Bhubaneswar (nearest)"

    def test_batch_allocation_priority_order(self):
        """Batch allocation should process critical zones before low zones."""
        zones = [
            {"id": 1, "name": "Low Zone",      "lat": 13.0, "lon": 80.0,
             "severity": "low",      "population_affected": 1000},
            {"id": 2, "name": "Critical Zone", "lat": 13.0, "lon": 80.0,
             "severity": "critical", "population_affected": 10000},
            {"id": 3, "name": "High Zone",     "lat": 13.0, "lon": 80.0,
             "severity": "high",     "population_affected": 5000},
        ]
        depots   = [{"id": 1, "name": "Depot", "lat": 13.0, "lon": 80.0}]
        inventory = {"food": 100000, "water": 200000}

        results = GreedyAllocator.allocate_batch(zones, depots, inventory)

        # Results should be ordered critical → high → low
        severities = [r["severity"] for r in results]
        assert severities == ["critical", "high", "low"]


# ---------------------------------------------------------------------------
# Integration tests for the API allocation endpoints
# ---------------------------------------------------------------------------
ZONE_PAYLOAD = {
    "name": "Test Zone for Allocation",
    "state": "Kerala",
    "latitude": 11.6854, "longitude": 76.1320,
    "disaster_type": "flood",
    "severity": "critical", "severity_score": 8.5,
    "population_affected": 10000, "population_total": 50000,
    "vulnerability_index": 0.60,
    "source": "test",
}

DEPOT_PAYLOAD = {
    "name": "Test Chennai Depot",
    "city": "Chennai", "state": "Tamil Nadu",
    "latitude": 13.0827, "longitude": 80.2707,
    "capacity_units": 200000,
}

RESOURCE_PAYLOAD = {
    "name": "Test Food Packets",
    "category": "food", "unit": "packets",
    "quantity_available": 50000, "quantity_total": 60000,
    "quantity_deployed": 10000,
}


class TestAllocationAPI:

    def test_optimizer_status(self, client):
        """GET /api/allocation/status should return online status."""
        r = client.get("/api/allocation/status")
        assert r.status_code == 200
        data = r.json()
        assert data["optimizer"] == "online"
        assert "algorithm" in data

    def test_optimize_zone_no_depots(self, client):
        """POST /api/allocation/optimize should return 503 when no depots."""
        # Create a zone
        r = client.post("/api/zones/", json=ZONE_PAYLOAD)
        zone_id = r.json()["id"]

        # With no depots, should get 503 (or a feasible=False plan)
        r = client.post(f"/api/allocation/optimize?zone_id={zone_id}")
        # Could be 503 (no depots) or 200 with infeasible plan
        assert r.status_code in (200, 503)

    def test_optimize_zone_with_depot_and_resources(self, client):
        """Full optimization flow: zone + depot + resources → allocation plan."""
        # Create zone
        rz = client.post("/api/zones/", json=ZONE_PAYLOAD)
        zone_id = rz.json()["id"]

        # Create depot
        rd = client.post("/api/depots/", json=DEPOT_PAYLOAD)
        depot_id = rd.json()["id"]

        # Create resource for that depot
        res_payload = dict(RESOURCE_PAYLOAD, depot_id=depot_id)
        client.post("/api/resources/", json=res_payload)

        # Now optimize
        r = client.post(f"/api/allocation/optimize?zone_id={zone_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        plan = data["allocation_plan"]
        assert plan["zone_id"] == zone_id
        assert "depot_id" in plan
        assert "distance_km" in plan
        assert "estimated_hours" in plan
        assert "resources" in plan
        assert isinstance(plan["resources"], list)
        assert isinstance(plan["warnings"], list)

    def test_optimize_zone_not_found(self, client):
        """POST /api/allocation/optimize?zone_id=99999 should return 404."""
        r = client.post("/api/allocation/optimize?zone_id=99999")
        assert r.status_code == 404

    def test_optimize_all_zones(self, client):
        """POST /api/allocation/optimize-all should return plans for all zones."""
        r = client.post("/api/allocation/optimize-all")
        assert r.status_code in (200, 503)
        if r.status_code == 200:
            data = r.json()
            assert "plans" in data
            assert "total_zones" in data

    def test_nearest_depot(self, client):
        """GET /api/allocation/nearest-depot should return sorted depots."""
        # Ensure zone and depot exist
        rz = client.post("/api/zones/", json=ZONE_PAYLOAD)
        zone_id = rz.json()["id"]
        client.post("/api/depots/", json=DEPOT_PAYLOAD)

        r = client.get(f"/api/allocation/nearest-depot?zone_id={zone_id}")
        assert r.status_code == 200
        data = r.json()
        assert "nearest" in data
        assert "all_depots_sorted" in data
        assert data["nearest"]["distance_km"] <= data["all_depots_sorted"][-1]["distance_km"]


# ---------------------------------------------------------------------------
# Analytics API tests
# ---------------------------------------------------------------------------
class TestAnalyticsAPI:

    def test_dashboard_endpoint(self, client):
        """GET /api/analytics/dashboard should return full dashboard data."""
        r = client.get("/api/analytics/dashboard")
        assert r.status_code == 200
        data = r.json()
        assert "zones" in data
        assert "resources" in data
        assert "teams" in data
        assert "depots" in data
        assert "events" in data

        zones_data = data["zones"]
        assert "active" in zones_data
        assert "total_affected" in zones_data
        assert "severity" in zones_data
        sev = zones_data["severity"]
        assert all(k in sev for k in ["critical", "high", "medium", "low"])

    def test_severity_trend(self, client):
        """GET /api/analytics/severity-trend should return distributions."""
        r = client.get("/api/analytics/severity-trend")
        assert r.status_code == 200
        data = r.json()
        assert "by_severity" in data
        assert "by_disaster_type" in data
        assert "score_distribution" in data
        assert "total_active_zones" in data

    def test_resource_utilization(self, client):
        """GET /api/analytics/resource-utilization should return utilization rates."""
        client.post("/api/resources/", json={
            "name": "Utilization Test Resource",
            "category": "water", "unit": "liters",
            "quantity_available": 7000, "quantity_total": 10000,
            "quantity_deployed": 3000,
        })

        r = client.get("/api/analytics/resource-utilization")
        assert r.status_code == 200
        data = r.json()
        assert "categories" in data
        assert "total_categories" in data
        for cat in data["categories"]:
            assert "utilization_pct" in cat
            assert "availability_pct" in cat
            assert "status" in cat

    def test_teams_overview(self, client):
        """GET /api/analytics/teams-overview should return team deployment data."""
        r = client.get("/api/analytics/teams-overview")
        assert r.status_code == 200
        data = r.json()
        assert "teams" in data
        assert "total" in data
        assert "deployed_count" in data

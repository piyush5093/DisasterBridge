"""
Test: Disaster Zones API
========================
Tests CRUD operations on /api/zones and demand prediction.
"""
import pytest


ZONE_PAYLOAD = {
    "name": "Test Zone — Kerala",
    "state": "Kerala",
    "district": "Wayanad",
    "latitude": 11.6854,
    "longitude": 76.1320,
    "area_sq_km": 200.0,
    "disaster_type": "flood",
    "severity": "critical",
    "severity_score": 8.5,
    "population_affected": 15000,
    "population_total": 100000,
    "vulnerability_index": 0.70,
    "source": "test",
}


class TestZonesAPI:

    def test_health_check(self, client):
        """Root endpoint should report online status."""
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "online"
        assert "modules" in data

    def test_list_zones_empty(self, client):
        """GET /api/zones/ should return empty list on fresh DB."""
        r = client.get("/api/zones/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_zone(self, client):
        """POST /api/zones/ should create and return a new zone."""
        r = client.post("/api/zones/", json=ZONE_PAYLOAD)
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == ZONE_PAYLOAD["name"]
        assert data["severity"] == "critical"
        assert data["id"] > 0
        return data["id"]

    def test_get_zone(self, client):
        """GET /api/zones/{id} should return the zone."""
        # Create first
        r = client.post("/api/zones/", json=ZONE_PAYLOAD)
        zone_id = r.json()["id"]

        r = client.get(f"/api/zones/{zone_id}")
        assert r.status_code == 200
        assert r.json()["id"] == zone_id

    def test_get_zone_not_found(self, client):
        """GET /api/zones/99999 should return 404."""
        r = client.get("/api/zones/99999")
        assert r.status_code == 404

    def test_update_zone(self, client):
        """PUT /api/zones/{id} should update severity."""
        r = client.post("/api/zones/", json=ZONE_PAYLOAD)
        zone_id = r.json()["id"]

        r = client.put(f"/api/zones/{zone_id}", json={
            "severity": "high",
            "severity_score": 7.0,
        })
        assert r.status_code == 200
        assert r.json()["severity"] == "high"

    def test_deactivate_zone(self, client):
        """DELETE /api/zones/{id} should deactivate (is_active=0)."""
        r = client.post("/api/zones/", json=ZONE_PAYLOAD)
        zone_id = r.json()["id"]

        r = client.delete(f"/api/zones/{zone_id}")
        assert r.status_code == 200
        assert r.json()["id"] == zone_id

    def test_zones_summary(self, client):
        """GET /api/zones/summary should return aggregated stats."""
        r = client.get("/api/zones/summary")
        assert r.status_code == 200
        data = r.json()
        assert "total_zones" in data
        assert "severity_breakdown" in data
        assert "total_affected" in data

    def test_zone_demand_prediction(self, client):
        """GET /api/zones/{id}/demand should return demand estimates."""
        r = client.post("/api/zones/", json=ZONE_PAYLOAD)
        zone_id = r.json()["id"]

        r = client.get(f"/api/zones/{zone_id}/demand")
        assert r.status_code == 200
        data = r.json()
        assert "demand" in data
        demand = data["demand"]
        assert "food_packets" in demand
        assert "water_liters" in demand
        assert "medical_kits" in demand
        assert "shelter_capacity" in demand
        assert "rescue_vehicles" in demand
        assert "personnel_needed" in demand
        assert demand["food_packets"] > 0, "Food demand should be > 0 for 15000 affected"
        assert demand["water_liters"] > 0

    def test_zone_demand_not_found(self, client):
        """GET /api/zones/99999/demand should return 404."""
        r = client.get("/api/zones/99999/demand")
        assert r.status_code == 404

    def test_filter_by_severity(self, client):
        """GET /api/zones/?severity=critical should filter results."""
        r = client.get("/api/zones/?severity=critical")
        assert r.status_code == 200
        zones = r.json()
        for z in zones:
            assert z["severity"] == "critical"

    def test_predictor_status(self, client):
        """GET /api/zones/predictor/status should return model info."""
        r = client.get("/api/zones/predictor/status")
        assert r.status_code == 200
        data = r.json()
        assert "model_ready" in data

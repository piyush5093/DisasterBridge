"""
Test: Resources API
===================
Tests resource CRUD, summary, and alerts endpoints.
"""
import pytest


DEPOT_PAYLOAD = {
    "name": "Test Depot Mumbai",
    "city": "Mumbai",
    "state": "Maharashtra",
    "latitude": 19.0760,
    "longitude": 72.8777,
    "capacity_units": 100000,
}

RESOURCE_PAYLOAD = {
    "name": "Food Packets (Test)",
    "category": "food",
    "unit": "packets",
    "quantity_available": 8000,
    "quantity_total": 10000,
    "quantity_deployed": 2000,
    "critical_threshold": 0.20,
}

CRITICAL_RESOURCE_PAYLOAD = {
    "name": "Medical Kits (Critical)",
    "category": "medical",
    "unit": "kits",
    "quantity_available": 100,
    "quantity_total": 1000,
    "quantity_deployed": 900,
    "critical_threshold": 0.20,
}


class TestResourcesAPI:

    def test_list_resources_empty(self, client):
        """GET /api/resources/ should return list."""
        r = client.get("/api/resources/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_resource(self, client):
        """POST /api/resources/ should create a resource."""
        r = client.post("/api/resources/", json=RESOURCE_PAYLOAD)
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == RESOURCE_PAYLOAD["name"]
        assert data["category"] == "food"
        assert data["quantity_available"] == 8000
        assert data["id"] > 0

    def test_get_resource(self, client):
        """GET /api/resources/{id} should return the resource."""
        r = client.post("/api/resources/", json=RESOURCE_PAYLOAD)
        rid = r.json()["id"]

        r = client.get(f"/api/resources/{rid}")
        assert r.status_code == 200
        assert r.json()["id"] == rid

    def test_get_resource_not_found(self, client):
        """GET /api/resources/99999 should return 404."""
        r = client.get("/api/resources/99999")
        assert r.status_code == 404

    def test_update_resource_quantity(self, client):
        """PUT /api/resources/{id} should update quantities."""
        r = client.post("/api/resources/", json=RESOURCE_PAYLOAD)
        rid = r.json()["id"]

        r = client.put(f"/api/resources/{rid}", json={
            "quantity_available": 5000,
            "quantity_deployed": 5000,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["quantity_available"] == 5000

    def test_resource_summary(self, client):
        """GET /api/resources/summary should return category breakdown."""
        # Ensure at least one resource exists
        client.post("/api/resources/", json=RESOURCE_PAYLOAD)

        r = client.get("/api/resources/summary")
        assert r.status_code == 200
        data = r.json()
        assert "categories" in data
        assert "total_items" in data
        assert data["total_items"] >= 1

    def test_resource_alerts_critical(self, client):
        """GET /api/resources/alerts should identify critical resources."""
        # Create a resource that's below threshold (10% available)
        client.post("/api/resources/", json=CRITICAL_RESOURCE_PAYLOAD)

        r = client.get("/api/resources/alerts")
        assert r.status_code == 200
        data = r.json()
        assert "count" in data
        assert "resources" in data
        # Critical resource (10% available vs 20% threshold) should appear
        assert data["count"] >= 1

    def test_filter_by_category(self, client):
        """GET /api/resources/?category=food should filter results."""
        client.post("/api/resources/", json=RESOURCE_PAYLOAD)
        r = client.get("/api/resources/?category=food")
        assert r.status_code == 200
        resources = r.json()
        for res in resources:
            assert res["category"] == "food"

    def test_create_depot(self, client):
        """POST /api/depots/ should create a depot."""
        r = client.post("/api/depots/", json=DEPOT_PAYLOAD)
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == DEPOT_PAYLOAD["name"]
        assert data["city"] == "Mumbai"
        assert data["id"] > 0

    def test_list_depots(self, client):
        """GET /api/depots/ should return active depots."""
        client.post("/api/depots/", json=DEPOT_PAYLOAD)
        r = client.get("/api/depots/")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_get_depot(self, client):
        """GET /api/depots/{id} should return the depot."""
        r = client.post("/api/depots/", json=DEPOT_PAYLOAD)
        did = r.json()["id"]

        r = client.get(f"/api/depots/{did}")
        assert r.status_code == 200
        assert r.json()["id"] == did

    def test_get_depot_not_found(self, client):
        """GET /api/depots/99999 should return 404."""
        r = client.get("/api/depots/99999")
        assert r.status_code == 404

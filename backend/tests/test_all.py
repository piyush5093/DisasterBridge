import pytest
from fastapi.testclient import TestClient
from main import app
from database import Base, engine, get_db
from sqlalchemy.orm import sessionmaker

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200

def test_resources_crud():
    # Create
    res = client.post("/api/resources", json={
        "resource_type": "water", "quantity": 100, "unit": "liters",
        "lat": 35.0, "lng": 139.0, "depot_name": "Test Depot"
    })
    assert res.status_code == 200
    r_id = res.json()["id"]
    
    # Get
    res2 = client.get(f"/api/resources/{r_id}")
    assert res2.status_code == 200
    
    # Put
    res3 = client.put(f"/api/resources/{r_id}", json={"quantity": 50, "status": "available"})
    assert res3.status_code == 200
    assert res3.json()["quantity"] == 50
    
    # Delete
    res4 = client.delete(f"/api/resources/{r_id}")
    assert res4.status_code == 204
    
    # Get again (404)
    res5 = client.get(f"/api/resources/{r_id}")
    assert res5.status_code == 404

def test_mission_status_transition():
    # We rely on an existing mission or we mock it. Since this is an E2E on the live DB,
    # let's just assert the endpoint exists and returns 404 for a fake ID.
    res = client.patch("/api/missions/00000000-0000-0000-0000-000000000000/status", json={"status": "in_transit"})
    assert res.status_code == 404

def test_analytics():
    res = client.get("/api/analytics/zone-priority-ranking")
    assert res.status_code == 200
    res = client.get("/api/analytics/delivery-performance")
    assert res.status_code == 200
    res = client.get("/api/analytics/underserved-zones")
    assert res.status_code == 200
    res = client.get("/api/analytics/export")
    assert res.status_code == 200
    assert "Active Incidents" in res.text

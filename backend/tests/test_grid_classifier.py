"""
Tests for app/services/zones/grid_classifier.py — the Milestone 1
severity-scoring logic. Pure-function tests (haversine, point-in-ring,
generate_grid, score_cell) run without any DB; the end-to-end
generate_and_score_grid test uses mongomock-motor.
"""

import pytest
import pytest_asyncio
from beanie import init_beanie
from mongomock_motor import AsyncMongoMockClient

from app.models.building_footprint import BuildingFootprint
from app.models.disaster_event import DisasterEvent, GeoPoint
from app.models.grid_cell import GridCell
from app.models.resource_inventory import ResourceInventory, ResourceStatus, ResourceType
from app.services.zones.grid_classifier import (
    _point_in_ring,
    generate_and_score_grid,
    generate_grid,
    haversine_km,
    score_cell,
)


@pytest_asyncio.fixture(autouse=True)
async def init_test_db():
    client = AsyncMongoMockClient()
    await init_beanie(
        database=client["grid_test_db"],
        document_models=[DisasterEvent, BuildingFootprint, ResourceInventory, GridCell],
    )
    yield


# --- Pure geometry/math helpers ---

def test_haversine_known_distance():
    # Kochi to Bengaluru is roughly 350km
    dist = haversine_km(76.28, 9.97, 77.59, 12.97)
    assert 300 < dist < 400


def test_haversine_zero_for_same_point():
    assert haversine_km(76.28, 9.97, 76.28, 9.97) == pytest.approx(0.0, abs=1e-9)


def test_point_in_ring_basic_square():
    square = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
    assert _point_in_ring(5, 5, square) is True
    assert _point_in_ring(15, 5, square) is False
    assert _point_in_ring(-1, -1, square) is False


def test_generate_grid_produces_expected_cell_count():
    # A ~10km x 10km bbox around the equator with 5km cells -> roughly 2x2 = 4 cells
    cells = generate_grid(min_lon=0.0, min_lat=0.0, max_lon=0.09, max_lat=0.09, cell_size_km=5.0)
    assert len(cells) >= 2  # at least a couple of cells; exact count depends on rounding

    for cell in cells:
        assert "geometry" in cell
        ring = cell["geometry"]["coordinates"][0]
        assert ring[0] == ring[-1]  # closed ring
        assert cell["geometry"]["type"] == "Polygon"


def test_generate_grid_cells_are_within_bbox():
    cells = generate_grid(min_lon=76.0, min_lat=9.0, max_lon=76.2, max_lat=9.2, cell_size_km=5.0)
    for cell in cells:
        ring = cell["geometry"]["coordinates"][0]
        for lon, lat in ring:
            assert 75.9 <= lon <= 76.3  # small tolerance
            assert 8.9 <= lat <= 9.3


# --- Severity scoring ---

def _make_event(event_type="EQ", severity_value=6.0, alert_level="Red", lon=76.28, lat=9.97, population=None):
    return DisasterEvent(
        source="TEST",
        external_event_id="1",
        event_type=event_type,
        severity_value=severity_value,
        alert_level=alert_level,
        location=GeoPoint(coordinates=[lon, lat]),
        population_exposed=population,
    )


def test_score_cell_no_inputs_gives_baseline_resource_component_only():
    result = score_cell(76.28, 9.97, [[76.0, 9.0], [76.5, 9.0], [76.5, 10.0], [76.0, 10.0], [76.0, 9.0]], [], [], [])

    assert result["event_component"] == 0.0
    assert result["building_component"] == 0.0
    assert result["population_component"] == 0.0
    assert result["resource_component"] == 10.0  # no resources known -> default moderate-high
    assert result["severity_score"] == 10.0


def test_score_cell_nearby_severe_event_increases_score():
    ring = [[76.0, 9.0], [76.5, 9.0], [76.5, 10.0], [76.0, 10.0], [76.0, 9.0]]
    event = _make_event(alert_level="Red", severity_value=7.0)

    result = score_cell(76.28, 9.97, ring, [event], [], [])

    assert result["event_component"] > 0
    assert str(event.id) in result["contributing_event_ids"]
    assert result["severity_score"] > 10.0  # baseline + event contribution


def test_score_cell_distant_event_does_not_contribute():
    ring = [[76.0, 9.0], [76.5, 9.0], [76.5, 10.0], [76.0, 10.0], [76.0, 9.0]]
    # Event far away (Delhi-ish), should be outside its own impact radius from Kochi
    far_event = _make_event(lon=77.1, lat=28.7, alert_level="Red", severity_value=5.0)

    result = score_cell(76.28, 9.97, ring, [far_event], [], [])

    assert result["event_component"] == 0.0
    assert result["contributing_event_ids"] == []


def test_score_cell_population_component_scales_with_log():
    ring = [[76.0, 9.0], [76.5, 9.0], [76.5, 10.0], [76.0, 10.0], [76.0, 9.0]]
    small_pop_event = _make_event(population=1000)
    large_pop_event = _make_event(population=1_000_000)

    small_result = score_cell(76.28, 9.97, ring, [small_pop_event], [], [])
    large_result = score_cell(76.28, 9.97, ring, [large_pop_event], [], [])

    assert large_result["population_component"] > small_result["population_component"]
    assert large_result["population_component"] <= 20.0  # capped


def test_score_cell_resource_component_scales_with_distance():
    ring = [[76.0, 9.0], [76.5, 9.0], [76.5, 10.0], [76.0, 10.0], [76.0, 9.0]]

    close_resource = ResourceInventory(
        depot_name="Close Depot",
        resource_type=ResourceType.WATER,
        quantity=100,
        unit="liters",
        location=GeoPoint(coordinates=[76.28, 9.97]),
        status=ResourceStatus.ACTIVE,
    )
    far_resource = ResourceInventory(
        depot_name="Far Depot",
        resource_type=ResourceType.WATER,
        quantity=100,
        unit="liters",
        location=GeoPoint(coordinates=[80.0, 13.0]),
        status=ResourceStatus.ACTIVE,
    )

    close_result = score_cell(76.28, 9.97, ring, [], [], [close_resource])
    far_result = score_cell(76.28, 9.97, ring, [], [], [far_resource])

    assert close_result["resource_component"] < far_result["resource_component"]
    assert close_result["nearest_resource_km"] < far_result["nearest_resource_km"]


def test_score_cell_caps_total_at_100():
    ring = [[76.0, 9.0], [76.5, 9.0], [76.5, 10.0], [76.0, 10.0], [76.0, 9.0]]
    events = [_make_event(alert_level="Red", severity_value=8.0, population=5_000_000) for _ in range(5)]
    far_resource = ResourceInventory(
        depot_name="Far",
        resource_type=ResourceType.WATER,
        quantity=1,
        unit="liters",
        location=GeoPoint(coordinates=[90.0, 30.0]),
    )

    result = score_cell(76.28, 9.97, ring, events, [], [far_resource])
    assert result["severity_score"] <= 100.0


# --- Full pipeline (mongomock) ---

@pytest.mark.asyncio
async def test_generate_and_score_grid_end_to_end():
    await DisasterEvent(
        source="TEST",
        external_event_id="1",
        event_type="EQ",
        severity_value=6.5,
        alert_level="Red",
        location=GeoPoint(coordinates=[76.28, 9.97]),
        is_current=True,
    ).insert()

    grid_run_id = await generate_and_score_grid(
        min_lon=76.2, min_lat=9.9, max_lon=76.35, max_lat=10.05, cell_size_km=5.0
    )

    cells = await GridCell.find(GridCell.grid_run_id == grid_run_id).to_list()
    assert len(cells) > 0
    assert all(0 <= c.severity_score <= 100 for c in cells)

    # At least one cell near the event should have a nonzero event_component
    assert any(c.event_component > 0 for c in cells)


@pytest.mark.asyncio
async def test_generate_and_score_grid_creates_separate_runs():
    id1 = await generate_and_score_grid(76.2, 9.9, 76.3, 10.0, cell_size_km=5.0)
    id2 = await generate_and_score_grid(76.2, 9.9, 76.3, 10.0, cell_size_km=5.0)

    assert id1 != id2
    count1 = await GridCell.find(GridCell.grid_run_id == id1).count()
    count2 = await GridCell.find(GridCell.grid_run_id == id2).count()
    assert count1 > 0 and count2 > 0

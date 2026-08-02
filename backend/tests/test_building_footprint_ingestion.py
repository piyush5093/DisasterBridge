"""Tests for app/services/ingestion/building_footprint_ingestion.py."""

import json
from pathlib import Path

import pytest
import pytest_asyncio
from beanie import init_beanie
from mongomock_motor import AsyncMongoMockClient

from app.models.building_footprint import BuildingFootprint
from app.services.ingestion.building_footprint_ingestion import normalize_element, upsert_footprints

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "overpass_buildings_sample.json"


def load_fixture() -> dict:
    with open(FIXTURE_PATH) as f:
        return json.load(f)


@pytest_asyncio.fixture(autouse=True)
async def init_test_db():
    client = AsyncMongoMockClient()
    await init_beanie(database=client["buildings_test_db"], document_models=[BuildingFootprint])
    yield


def test_way_normalizes_to_closed_polygon():
    data = load_fixture()
    way = data["elements"][0]

    normalized = normalize_element(way)

    assert normalized is not None
    assert normalized["osm_id"] == 20714383
    assert normalized["osm_type"] == "way"
    assert normalized["building_type"] == "residential"
    ring = normalized["geometry"]["coordinates"][0]
    assert ring[0] == ring[-1]  # closed ring
    assert ring[0] == [77.5941, 12.9711]  # lon, lat order (flipped from Overpass's lat, lon)


def test_standalone_node_normalizes_to_point():
    data = load_fixture()
    node = data["elements"][2]

    normalized = normalize_element(node)

    assert normalized is not None
    assert normalized["osm_type"] == "node"
    assert normalized["geometry"] == {"type": "Point", "coordinates": [77.5975, 12.9745]}
    assert normalized["building_type"] == "yes"


def test_way_with_too_few_points_is_skipped():
    data = load_fixture()
    degenerate_way = data["elements"][3]  # only 2 geometry points

    assert normalize_element(degenerate_way) is None


@pytest.mark.asyncio
async def test_upsert_footprints_end_to_end():
    data = load_fixture()

    result = await upsert_footprints(data["elements"])

    assert result["fetched"] == 4
    assert result["created"] == 3  # 2 ways + 1 node; the degenerate way is skipped
    assert result["skipped"] == 1

    count = await BuildingFootprint.find_all().count()
    assert count == 3


@pytest.mark.asyncio
async def test_upsert_is_idempotent():
    data = load_fixture()

    first = await upsert_footprints(data["elements"])
    second = await upsert_footprints(data["elements"])

    assert first["created"] == 3
    assert second["created"] == 0
    assert second["updated"] == 3

    count = await BuildingFootprint.find_all().count()
    assert count == 3  # no duplicates

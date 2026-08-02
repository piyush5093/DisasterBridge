"""
Unit tests for GDACS feature normalization (app/services/ingestion/gdacs_ingestion.py).

These test the parsing/mapping logic in isolation using a realistic
fixture (tests/fixtures/gdacs_sample_response.json) built from GDACS's
documented GeoJSON schema. They do NOT hit the real GDACS API or require
a database — see README "Day 2" section for how to test the full
ingest-and-store flow against a live DB.
"""

import json
from pathlib import Path

from shapely.geometry import shape

from app.services.ingestion.gdacs_ingestion import normalize_feature

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "gdacs_sample_response.json"


def load_fixture() -> dict:
    with open(FIXTURE_PATH) as f:
        return json.load(f)


def test_normalizes_point_feature_flood():
    data = load_fixture()
    feature = data["features"][0]  # FL event, Point geometry

    normalized = normalize_feature(feature)

    assert normalized is not None
    assert normalized["source"] == "GDACS"
    assert normalized["external_event_id"] == "1102983"
    assert normalized["episode_id"] == "1"
    assert normalized["event_type"] == "FL"
    assert normalized["event_name"] == "Flood in India"
    assert normalized["alert_level"] == "Orange"
    assert normalized["alert_score"] == 2.4
    assert normalized["severity_value"] == 3.2
    assert normalized["severity_unit"] == "m"
    assert normalized["population_exposed"] == 185000
    assert normalized["country"] == "India"
    assert normalized["iso3"] == "IND"
    assert normalized["from_date"].year == 2026
    assert normalized["source_url"].startswith("https://www.gdacs.org/report.aspx")
    # raw_data must preserve everything, untouched
    assert normalized["raw_data"]["eventid"] == 1102983


def test_normalizes_point_feature_earthquake_minimal_fields():
    data = load_fixture()
    feature = data["features"][1]  # EQ event, fewer optional fields

    normalized = normalize_feature(feature)

    assert normalized is not None
    assert normalized["event_type"] == "EQ"
    assert normalized["severity_unit"] == "M"
    assert normalized["glide_number"] is None  # not present in this fixture entry


def test_polygon_geometry_reduced_to_centroid_point():
    data = load_fixture()
    feature = data["features"][2]  # TC event with Polygon geometry

    normalized = normalize_feature(feature)

    assert normalized is not None
    # location must be a GeoJSON Point wrapping the polygon's centroid,
    # not the original polygon geometry
    location = normalized["location"]
    assert location["type"] == "Point"
    lon, lat = location["coordinates"]

    expected_centroid = shape(feature["geometry"]).centroid
    assert round(lon, 4) == round(expected_centroid.x, 4)
    assert round(lat, 4) == round(expected_centroid.y, 4)


def test_malformed_feature_missing_required_fields_is_skipped():
    data = load_fixture()
    feature = data["features"][3]  # missing eventid and geometry

    normalized = normalize_feature(feature)

    assert normalized is None

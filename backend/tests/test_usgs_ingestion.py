"""
Unit tests for USGS feature normalization (app/services/ingestion/usgs_ingestion.py).

Fixture schema (tests/fixtures/usgs_sample_response.json) matches USGS's
confirmed live GeoJSON structure: properties.{mag, place, time, updated,
alert, sig, magType, type, title, url, detail}, geometry.coordinates =
[lon, lat, depth_km], top-level `id`.
"""

import json
from pathlib import Path

from app.services.ingestion.usgs_ingestion import normalize_feature

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "usgs_sample_response.json"


def load_fixture() -> dict:
    with open(FIXTURE_PATH) as f:
        return json.load(f)


def test_normalizes_significant_earthquake():
    data = load_fixture()
    feature = data["features"][0]  # M6.5 Mexico

    normalized = normalize_feature(feature)

    assert normalized is not None
    assert normalized["source"] == "USGS"
    assert normalized["external_event_id"] == "us7000rq15"
    assert normalized["episode_id"] == "0"
    assert normalized["event_type"] == "EQ"
    assert normalized["event_name"] == "M 6.5 - 7 km ESE of Barrio Nuevo de los Muertos, Mexico"
    assert normalized["alert_level"] == "Orange"
    assert normalized["alert_score"] == 782
    assert normalized["severity_value"] == 6.5
    assert normalized["severity_unit"] == "MW"
    assert normalized["country"] is None  # USGS gives no structured country field
    assert normalized["source_url"] == "https://earthquake.usgs.gov/earthquakes/eventpage/us7000rq15"
    assert normalized["is_current"] is True


def test_geometry_includes_depth_in_raw_data_but_point_is_lon_lat():
    data = load_fixture()
    feature = data["features"][0]

    normalized = normalize_feature(feature)
    location = normalized["location"]

    assert location["type"] == "Point"
    lon, lat = location["coordinates"]
    assert round(lon, 3) == -99.303  # longitude
    assert round(lat, 3) == 16.902  # latitude
    assert normalized["raw_data"]["depth_km"] == 18.0


def test_epoch_millis_converted_to_utc_datetime():
    data = load_fixture()
    feature = data["features"][0]

    normalized = normalize_feature(feature)

    assert normalized["from_date"] is not None
    assert normalized["from_date"].tzinfo is not None
    assert normalized["from_date"] == normalized["to_date"]  # instantaneous event


def test_minor_earthquake_with_no_alert_or_felt_reports():
    data = load_fixture()
    feature = data["features"][1]  # M2.1, no alert/felt/cdi/mmi

    normalized = normalize_feature(feature)

    assert normalized is not None
    assert normalized["alert_level"] is None
    assert normalized["severity_value"] == 2.1
    assert normalized["severity_unit"] == "MD"


def test_feature_missing_id_or_geometry_is_skipped():
    malformed = {"type": "Feature", "properties": {"mag": 5.0}, "geometry": None, "id": None}
    assert normalize_feature(malformed) is None

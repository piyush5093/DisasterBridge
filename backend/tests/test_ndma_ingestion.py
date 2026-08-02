"""
Unit tests for app/services/ingestion/ndma_ingestion.py, using the parsed
CAP fixtures from test_cap_parser.py.
"""

from pathlib import Path

from app.services.ingestion.ndma_ingestion import _map_event_type, normalize_alert
from app.utils.cap_parser import parse_cap_alert

FIXTURES = Path(__file__).parent / "fixtures"


def load_alert(name: str):
    with open(FIXTURES / name, "rb") as f:
        return parse_cap_alert(f.read())


def test_normalizes_flood_alert():
    alert = load_alert("cap_alert_flood.xml")
    normalized = normalize_alert(alert)

    assert normalized is not None
    assert normalized["source"] == "NDMA"
    assert normalized["external_event_id"] == "NDMA-2026-FL-000123"
    assert normalized["event_type"] == "FL"
    assert normalized["alert_level"] == "Red"  # Severe -> Red
    assert normalized["country"] == "India"
    assert normalized["iso3"] == "IND"
    assert normalized["is_current"] is True  # status=Actual, msgType=Alert


def test_cancelled_alert_is_not_current():
    alert = load_alert("cap_alert_cyclone_circle.xml")
    normalized = normalize_alert(alert)

    assert normalized is not None
    assert normalized["event_type"] == "TC"
    assert normalized["alert_level"] == "Orange"  # Moderate -> Orange
    assert normalized["is_current"] is False  # msgType=Cancel


def test_geom_point_matches_parsed_centroid():
    alert = load_alert("cap_alert_flood.xml")
    normalized = normalize_alert(alert)

    location = normalized["location"]
    assert location["type"] == "Point"
    lon, lat = location["coordinates"]
    assert (round(lon, 4), round(lat, 4)) == (
        round(alert.points[0][0], 4),
        round(alert.points[0][1], 4),
    )


def test_event_type_keyword_mapping():
    assert _map_event_type("Flash Flood Warning") == "FL"
    assert _map_event_type("Cyclone Alert") == "TC"
    assert _map_event_type("Heavy Rainfall Warning") == "FL"
    assert _map_event_type("Landslide Advisory") == "LS"
    assert _map_event_type(None) == "OT"
    assert _map_event_type("Something Unrecognized") == "OT"

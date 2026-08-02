"""
Unit tests for app/utils/cap_parser.py against hand-built CAP v1.2
fixtures. CAP is a stable public OASIS standard (independent of NDMA),
so these fixtures are built directly to spec rather than needing a live
sample — unlike GDACS/USGS where field names had to be confirmed against
a real response.
"""

from pathlib import Path

from app.utils.cap_parser import parse_cap_alert

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> bytes:
    with open(FIXTURES / name, "rb") as f:
        return f.read()


def test_parses_flood_alert_with_polygon():
    alert = parse_cap_alert(load("cap_alert_flood.xml"))

    assert alert is not None
    assert alert.identifier == "NDMA-2026-FL-000123"
    assert alert.sender == "ndma.gov.in"
    assert alert.status == "Actual"
    assert alert.msg_type == "Alert"
    assert alert.event == "Flood Warning"
    assert alert.severity == "Severe"
    assert alert.urgency == "Immediate"
    assert alert.headline == "Severe Flood Warning for Kerala Districts"
    assert alert.area_desc == "Ernakulam and Alappuzha Districts, Kerala"
    assert alert.sent is not None
    assert alert.effective is not None
    assert alert.expires is not None


def test_polygon_centroid_is_lon_lat_order():
    """CAP polygon text is 'lat,lon lat,lon ...' — confirm we correctly
    flip it to (lon, lat) for consistency with GeoJSON/PostGIS storage."""
    alert = parse_cap_alert(load("cap_alert_flood.xml"))

    assert len(alert.points) == 1
    lon, lat = alert.points[0]
    # Polygon spans lat 9.85-10.05, lon 76.28-76.45 -> centroid should be within that box
    assert 76.28 <= lon <= 76.45
    assert 9.85 <= lat <= 10.05


def test_parses_circle_geometry_and_cancel_msgtype():
    alert = parse_cap_alert(load("cap_alert_cyclone_circle.xml"))

    assert alert is not None
    assert alert.msg_type == "Cancel"
    assert alert.event == "Cyclone Alert"
    assert len(alert.points) == 1
    lon, lat = alert.points[0]
    assert round(lon, 1) == 85.8
    assert round(lat, 1) == 19.8


def test_non_alert_root_returns_none():
    assert parse_cap_alert(b"<not-an-alert><foo/></not-an-alert>") is None


def test_malformed_xml_returns_none():
    assert parse_cap_alert(b"<alert><identifier>broken") is None

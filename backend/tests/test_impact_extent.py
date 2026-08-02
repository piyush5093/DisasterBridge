"""Unit tests for app/services/impact/extent_calculator.py."""

import math

from app.services.impact.extent_calculator import (
    bbox_from_polygon,
    circle_polygon_geojson,
    compute_impact_extent,
    estimate_impact_radius_km,
)


def test_earthquake_radius_scales_with_magnitude():
    small = estimate_impact_radius_km("EQ", 4.5, None)
    large = estimate_impact_radius_km("EQ", 7.0, None)
    assert large > small
    assert small >= 5.0  # floor applies


def test_earthquake_radius_floor_for_tiny_magnitude():
    assert estimate_impact_radius_km("EQ", 2.0, None) == 5.0


def test_unrecognized_type_falls_back_to_alert_level():
    assert estimate_impact_radius_km("OT", None, "Red") == 100.0
    assert estimate_impact_radius_km("OT", None, "Orange") == 50.0
    assert estimate_impact_radius_km("OT", None, None) == 30.0  # default fallback


def test_drought_area_converted_to_equivalent_radius():
    # DR severity_value is an area in km² (per GDACS's severitydata) —
    # confirm it's treated as area, not linear radius.
    area_km2 = 488851.0  # from the live GDACS DR fixture (Day 2)
    radius = estimate_impact_radius_km("DR", area_km2, None)
    expected = math.sqrt(area_km2 / math.pi)
    assert round(radius, 1) == round(expected, 1)


def test_circle_polygon_is_closed_ring_centered_correctly():
    polygon = circle_polygon_geojson(lon=77.5, lat=12.9, radius_km=50, num_points=16)

    assert polygon["type"] == "Polygon"
    ring = polygon["coordinates"][0]
    assert ring[0] == ring[-1]  # closed ring
    assert len(ring) == 17  # num_points + closing point

    lons = [p[0] for p in ring[:-1]]
    lats = [p[1] for p in ring[:-1]]
    center_lon = sum(lons) / len(lons)
    center_lat = sum(lats) / len(lats)
    assert round(center_lon, 1) == 77.5
    assert round(center_lat, 1) == 12.9


def test_larger_radius_produces_larger_bbox():
    small = circle_polygon_geojson(0, 0, 10)
    large = circle_polygon_geojson(0, 0, 100)

    small_bbox = bbox_from_polygon(small)
    large_bbox = bbox_from_polygon(large)

    small_width = small_bbox[2] - small_bbox[0]
    large_width = large_bbox[2] - large_bbox[0]
    assert large_width > small_width


def test_compute_impact_extent_end_to_end():
    extent = compute_impact_extent("EQ", 76.9, 18.0, severity_value=6.5, alert_level="Orange")
    assert extent["type"] == "Polygon"

    bbox = bbox_from_polygon(extent)
    assert bbox[0] < 76.9 < bbox[2]  # center longitude within bbox
    assert bbox[1] < 18.0 < bbox[3]  # center latitude within bbox

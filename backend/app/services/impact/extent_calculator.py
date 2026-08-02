"""
Geospatial impact extent estimation.

⚠️ HONESTY NOTE: the radius formulas below (`estimate_impact_radius_km`)
are simplified, clearly-labeled PLACEHOLDER heuristics, not real hazard
models. A genuine earthquake shaking-extent needs an attenuation model
(USGS ShakeMap-style), a real flood extent needs hydrological modeling
or the NDWI satellite analysis from Day 4, and a real cyclone extent
needs wind-radius forecast data. What's implemented here gives every
event *some* reasonable-looking extent polygon for the dashboard/map to
render immediately — useful for demoing the pipeline end-to-end — but
should be replaced per-hazard-type as real models are integrated
(the NDWI flood-extent imagery from Day 4 is the natural first
replacement for `event_type == "FL"`).

Geometry note: `_circle_polygon` uses a simple equirectangular
(per-axis degrees-per-km) approximation rather than a true geodesic
buffer. This is accurate to a few percent at the regional scale this
project operates at (tens to ~200km) and breaks down near the poles or
at very large radii — acceptable here, called out rather than presented
as precise.
"""

import math

KM_PER_DEG_LAT = 111.32

# Coarse placeholder radius by alert level, used as a fallback when an
# event type has no more specific formula below.
_ALERT_LEVEL_FALLBACK_RADIUS_KM = {"Red": 100.0, "Orange": 50.0, "Green": 20.0}


def estimate_impact_radius_km(event_type: str, severity_value: float | None, alert_level: str | None) -> float:
    """Best-effort, clearly-approximate impact radius in km. See module docstring."""
    if event_type == "EQ" and severity_value:
        # Placeholder: bigger magnitude -> wider felt/shaking radius.
        # Real implementation: USGS ShakeMap intensity contours.
        return max(5.0, (severity_value - 4.0) * 40.0)

    if event_type == "TC" and severity_value:
        # severity_value here is wind speed (km/h, per GDACS's severitydata).
        # Placeholder: scale wind speed into a rough storm-radius proxy.
        return max(30.0, severity_value * 1.5)

    if event_type in ("FL", "DR") and severity_value:
        # For DR, severity_value from NDMA/GDACS is often already an area
        # (km²) rather than a radius — treat it as an area and back out
        # an equivalent circle radius rather than misusing it directly.
        return max(15.0, math.sqrt(severity_value / math.pi))

    return _ALERT_LEVEL_FALLBACK_RADIUS_KM.get(alert_level or "", 30.0)


def circle_polygon_geojson(lon: float, lat: float, radius_km: float, num_points: int = 48) -> dict:
    """
    Approximate geodesic circle of `radius_km` around (lon, lat) as a
    GeoJSON Polygon, using per-axis equirectangular scaling (see module
    docstring for accuracy caveats).
    """
    lat_rad = math.radians(lat)
    km_per_deg_lon = KM_PER_DEG_LAT * math.cos(lat_rad)
    if abs(km_per_deg_lon) < 1e-6:
        km_per_deg_lon = 1e-6  # avoid div-by-zero at the poles

    ring = []
    for i in range(num_points):
        angle = 2 * math.pi * i / num_points
        d_lon = (radius_km * math.cos(angle)) / km_per_deg_lon
        d_lat = (radius_km * math.sin(angle)) / KM_PER_DEG_LAT
        ring.append([lon + d_lon, lat + d_lat])
    ring.append(ring[0])  # GeoJSON polygons must be closed rings

    return {"type": "Polygon", "coordinates": [ring]}


def compute_impact_extent(
    event_type: str,
    longitude: float,
    latitude: float,
    severity_value: float | None,
    alert_level: str | None,
) -> dict:
    """Full pipeline: estimate radius, then build the buffered polygon."""
    radius_km = estimate_impact_radius_km(event_type, severity_value, alert_level)
    return circle_polygon_geojson(longitude, latitude, radius_km)


def bbox_from_polygon(polygon_geojson: dict) -> tuple[float, float, float, float]:
    """(min_lon, min_lat, max_lon, max_lat) — handy for feeding Day 4's
    satellite imagery endpoints, which take a bounding box."""
    coords = polygon_geojson["coordinates"][0]
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return (min(lons), min(lats), max(lons), max(lats))

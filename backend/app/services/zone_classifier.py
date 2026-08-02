"""
Zone Classifier Service
Converts raw disaster event data into classified DisasterZone objects
with severity scoring based on magnitude, alert level, and affected area
"""

from typing import Dict, Any, Optional
from app.models.zone import SeverityLevel, DisasterType
from app.core.config import settings


GDACS_ALERT_MAP = {
    "Red":    10.0,
    "Orange": 7.0,
    "Green":  4.0,
}

USGS_MAGNITUDE_MAP = [
    (7.0, 10.0),   # M >= 7.0 → score 10
    (6.0, 8.0),
    (5.0, 6.0),
    (4.0, 4.0),
    (0.0, 2.0),
]

INDIA_STATES = {
    "Kerala", "Tamil Nadu", "Andhra Pradesh", "Telangana", "Karnataka",
    "Maharashtra", "Gujarat", "Odisha", "West Bengal", "Assam",
    "Bihar", "Uttar Pradesh", "Rajasthan", "Madhya Pradesh",
    "Uttarakhand", "Himachal Pradesh", "Jammu and Kashmir",
    "Manipur", "Nagaland", "Mizoram", "Tripura", "Meghalaya",
    "Arunachal Pradesh", "Sikkim", "Goa", "Punjab", "Haryana",
    "Jharkhand", "Chhattisgarh",
}


def _severity_from_score(score: float) -> str:
    """Convert numeric score (0–10) to severity label."""
    if score >= settings.CRITICAL_SCORE_MIN:
        return SeverityLevel.CRITICAL
    elif score >= settings.HIGH_SCORE_MIN:
        return SeverityLevel.HIGH
    elif score >= settings.MEDIUM_SCORE_MIN:
        return SeverityLevel.MEDIUM
    return SeverityLevel.LOW


def _disaster_type_from_gdacs(event_type: str) -> str:
    mapping = {
        "FL": DisasterType.FLOOD,
        "EQ": DisasterType.EARTHQUAKE,
        "TC": DisasterType.CYCLONE,
        "LS": DisasterType.LANDSLIDE,
        "DR": DisasterType.DROUGHT,
    }
    return mapping.get(event_type.upper(), DisasterType.OTHER)


def classify_gdacs_event(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse a GDACS event dict and return zone classification data.
    Returns None if the event is not India-relevant.
    """
    try:
        alert_level = event.get("alertlevel", "Green")
        score       = GDACS_ALERT_MAP.get(alert_level, 2.0)

        # Boost score based on affected population
        pop = event.get("population", {})
        affected = pop.get("affected", 0) if isinstance(pop, dict) else 0
        if affected > 100_000:
            score = min(10.0, score + 1.5)
        elif affected > 10_000:
            score = min(10.0, score + 0.5)

        country = event.get("country", "")
        region  = event.get("name", "") or event.get("title", "")

        # Determine state (best-effort matching)
        state = "India"
        for s in INDIA_STATES:
            if s.lower() in region.lower():
                state = s
                break

        zone_data = {
            "name":                 region or f"Disaster Zone — {country}",
            "state":                state,
            "district":             None,
            "latitude":             float(event.get("latitude",  0.0)),
            "longitude":            float(event.get("longitude", 0.0)),
            "disaster_type":        _disaster_type_from_gdacs(event.get("eventtype", "FL")),
            "severity":             _severity_from_score(score),
            "severity_score":       round(score, 2),
            "population_affected":  int(affected),
            "population_total":     0,
            "vulnerability_index":  0.0,
            "source":               "gdacs",
            "source_event_id":      str(event.get("eventid", "")),
            "description":          event.get("htmldescription", ""),
        }
        return zone_data

    except Exception as e:
        print(f"[ZoneClassifier] GDACS parse error: {e}")
        return None


def classify_usgs_event(feature: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse a USGS GeoJSON feature and return zone classification data.
    """
    try:
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [0, 0, 0])

        magnitude = props.get("mag", 0.0) or 0.0
        score = 2.0
        for threshold, s in USGS_MAGNITUDE_MAP:
            if magnitude >= threshold:
                score = s
                break

        place = props.get("place", "Unknown Location")
        state = "India"
        for s in INDIA_STATES:
            if s.lower() in place.lower():
                state = s
                break

        zone_data = {
            "name":              f"Earthquake — {place}",
            "state":             state,
            "district":          None,
            "latitude":          float(coords[1]),
            "longitude":         float(coords[0]),
            "disaster_type":     DisasterType.EARTHQUAKE,
            "severity":          _severity_from_score(score),
            "severity_score":    round(score, 2),
            "population_affected": 0,
            "population_total":    0,
            "vulnerability_index": 0.0,
            "source":            "usgs",
            "source_event_id":   feature.get("id", ""),
            "description":       f"M{magnitude} earthquake. {place}",
        }
        return zone_data

    except Exception as e:
        print(f"[ZoneClassifier] USGS parse error: {e}")
        return None


def compute_vulnerability_index(
    pct_elderly: float    = 0.0,
    pct_children: float   = 0.0,
    pct_medical: float    = 0.0,
) -> float:
    """
    Weighted vulnerability index (0–1).
    Weights: elderly=0.35, children=0.40, medically dependent=0.25
    """
    index = (pct_elderly * 0.35) + (pct_children * 0.40) + (pct_medical * 0.25)
    return round(min(1.0, max(0.0, index)), 4)

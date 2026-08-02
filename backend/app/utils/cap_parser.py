"""
Parser for CAP (Common Alerting Protocol) v1.2 XML alerts.

CAP is a stable, public OASIS standard (not NDMA-specific) — the same
format used by NOAA, Google Public Alerts, and India's own SACHET portal
(sachet.ndma.gov.in), which publishes NDMA alerts as CAP XML. Namespace,
element names, and structure below are per the OASIS CAP v1.2
specification, independent of any single publisher.

An <alert> has one <info> block per language (we take the first — NDMA
alerts include English and often a regional language). Each <info> has
zero or more <area> blocks, each of which may contain <polygon> and/or
<circle> geometry.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from xml.etree import ElementTree as ET

CAP_NS = {"cap": "urn:oasis:names:tc:emergency:cap:1.2"}


@dataclass
class ParsedCapAlert:
    identifier: str
    sender: str | None
    sent: datetime | None
    status: str | None  # Actual | Exercise | System | Test | Draft
    msg_type: str | None  # Alert | Update | Cancel | Ack | Error
    scope: str | None  # Public | Restricted | Private

    event: str | None = None
    urgency: str | None = None  # Immediate | Expected | Future | Past | Unknown
    severity: str | None = None  # Extreme | Severe | Moderate | Minor | Unknown
    certainty: str | None = None  # Observed | Likely | Possible | Unlikely | Unknown
    effective: datetime | None = None
    expires: datetime | None = None
    headline: str | None = None
    description: str | None = None
    instruction: str | None = None
    sender_name: str | None = None

    area_desc: str | None = None
    # (lon, lat) centroids of every polygon/circle in the first area block
    points: list[tuple[float, float]] = field(default_factory=list)

    raw_properties: dict[str, Any] = field(default_factory=dict)


def _text(el: ET.Element | None) -> str | None:
    if el is None or el.text is None:
        return None
    stripped = el.text.strip()
    return stripped or None


def _parse_cap_datetime(value: str | None) -> datetime | None:
    """CAP datetimes are ISO-8601 with a timezone offset, e.g.
    '2026-07-24T14:30:00+05:30'. Python's fromisoformat handles this
    natively (3.11+) including the +HH:MM form."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _polygon_centroid(coord_text: str) -> tuple[float, float] | None:
    """CAP <polygon> text is space-separated 'lat,lon' pairs (note:
    CAP uses lat,lon order, the OPPOSITE of GeoJSON's lon,lat)."""
    pairs = []
    for token in coord_text.strip().split():
        parts = token.split(",")
        if len(parts) != 2:
            continue
        try:
            lat, lon = float(parts[0]), float(parts[1])
            pairs.append((lon, lat))
        except ValueError:
            continue
    if not pairs:
        return None
    avg_lon = sum(p[0] for p in pairs) / len(pairs)
    avg_lat = sum(p[1] for p in pairs) / len(pairs)
    return (avg_lon, avg_lat)


def _circle_center(circle_text: str) -> tuple[float, float] | None:
    """CAP <circle> text is 'lat,lon radius_km', e.g. '19.076,72.877 25'."""
    try:
        point_part = circle_text.strip().split()[0]
        lat, lon = point_part.split(",")
        return (float(lon), float(lat))
    except (ValueError, IndexError):
        return None


def parse_cap_alert(xml_bytes: bytes) -> ParsedCapAlert | None:
    """
    Parse one CAP v1.2 XML document (as returned by NDMA's FetchXMLFile
    endpoint) into a ParsedCapAlert. Returns None if the document doesn't
    look like a valid CAP <alert> root element.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return None

    # Namespace may or may not be declared explicitly depending on the
    # publisher; strip it from the tag name to check robustly.
    tag = root.tag.split("}")[-1]
    if tag != "alert":
        return None

    def find(el: ET.Element, path: str) -> ET.Element | None:
        # Try namespaced first, then fall back to no-namespace (some
        # publishers omit the xmlns on individual elements).
        found = el.find(f"cap:{path}", CAP_NS)
        return found if found is not None else el.find(path)

    identifier = _text(find(root, "identifier"))
    if not identifier:
        return None

    sender = _text(find(root, "sender"))
    sent = _parse_cap_datetime(_text(find(root, "sent")))
    status = _text(find(root, "status"))
    msg_type = _text(find(root, "msgType"))
    scope = _text(find(root, "scope"))

    info_el = find(root, "info")
    alert = ParsedCapAlert(
        identifier=identifier,
        sender=sender,
        sent=sent,
        status=status,
        msg_type=msg_type,
        scope=scope,
    )

    if info_el is not None:
        alert.event = _text(find(info_el, "event"))
        alert.urgency = _text(find(info_el, "urgency"))
        alert.severity = _text(find(info_el, "severity"))
        alert.certainty = _text(find(info_el, "certainty"))
        alert.effective = _parse_cap_datetime(_text(find(info_el, "effective")))
        alert.expires = _parse_cap_datetime(_text(find(info_el, "expires")))
        alert.headline = _text(find(info_el, "headline"))
        alert.description = _text(find(info_el, "description"))
        alert.instruction = _text(find(info_el, "instruction"))
        alert.sender_name = _text(find(info_el, "senderName"))

        area_el = find(info_el, "area")
        if area_el is not None:
            alert.area_desc = _text(find(area_el, "areaDesc"))

            polygon_els = area_el.findall("cap:polygon", CAP_NS) or area_el.findall("polygon")
            for poly_el in polygon_els:
                centroid = _polygon_centroid(poly_el.text or "")
                if centroid:
                    alert.points.append(centroid)

            circle_els = area_el.findall("cap:circle", CAP_NS) or area_el.findall("circle")
            for circle_el in circle_els:
                center = _circle_center(circle_el.text or "")
                if center:
                    alert.points.append(center)

    alert.raw_properties = {
        "identifier": identifier,
        "sender": sender,
        "sent": sent.isoformat() if sent else None,
        "status": status,
        "msgType": msg_type,
        "scope": scope,
        "event": alert.event,
        "urgency": alert.urgency,
        "severity": alert.severity,
        "certainty": alert.certainty,
        "effective": alert.effective.isoformat() if alert.effective else None,
        "expires": alert.expires.isoformat() if alert.expires else None,
        "headline": alert.headline,
        "description": alert.description,
        "instruction": alert.instruction,
        "senderName": alert.sender_name,
        "areaDesc": alert.area_desc,
    }

    return alert

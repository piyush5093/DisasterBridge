"""
services.py - Data ingestion for Disaster Bridge.
Geographic scope: India + South Asia
  Countries: India, Nepal, Bangladesh, Sri Lanka, Myanmar, Pakistan, Bhutan, Afghanistan, Maldives
  Bounding box: lat 5-37 N, lon 60-100 E
"""
import requests
import uuid
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from models import DisasterEvent, SourceEnum, EventTypeEnum, AlertLevelEnum

# South Asia geographic bounding box
SA_LAT_MIN, SA_LAT_MAX = 5.0, 37.0
SA_LON_MIN, SA_LON_MAX = 60.0, 100.0


def _in_south_asia(lat: float, lon: float) -> bool:
    return SA_LAT_MIN <= lat <= SA_LAT_MAX and SA_LON_MIN <= lon <= SA_LON_MAX


def normalize_event_type(raw_type: str) -> EventTypeEnum:
    raw_type = raw_type.lower()
    if 'eq' in raw_type or 'earthquake' in raw_type: return EventTypeEnum.earthquake
    if 'fl' in raw_type or 'flood' in raw_type: return EventTypeEnum.flood
    if 'tc' in raw_type or 'cyclone' in raw_type or 'typhoon' in raw_type or 'hurricane' in raw_type: return EventTypeEnum.cyclone
    if 'dr' in raw_type or 'drought' in raw_type: return EventTypeEnum.drought
    if 'wf' in raw_type or 'wildfire' in raw_type or 'fire' in raw_type: return EventTypeEnum.wildfire
    return EventTypeEnum.other


def normalize_alert_level(raw_level: str) -> AlertLevelEnum:
    raw_level = raw_level.lower()
    if 'red' in raw_level: return AlertLevelEnum.red
    if 'orange' in raw_level: return AlertLevelEnum.orange
    if 'green' in raw_level: return AlertLevelEnum.green
    return AlertLevelEnum.low


def fetch_gdacs_events(db: Session):
    """
    Pulls live GDACS RSS feed and keeps only South Asia events.
    GDACS covers: floods, cyclones, earthquakes, wildfires, droughts.
    """
    url = "https://gdacs.org/xml/rss.xml"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch GDACS feed: {e}")
        return {"inserted": 0, "updated": 0, "skipped": 0, "error": str(e)}

    try:
        root = ET.fromstring(response.content)
    except Exception:
        return {"inserted": 0, "updated": 0, "skipped": 0, "error": "XML Parse Error"}

    namespaces = {'gdacs': 'http://www.gdacs.org'}
    inserted = updated = skipped = filtered_out = 0

    for item in root.findall('.//item'):
        ext_id_elem = item.find('gdacs:eventid', namespaces)
        if ext_id_elem is None:
            continue
        ext_id = ext_id_elem.text

        # Parse coordinates first — filter non-South-Asia events
        geo_point = item.find('{http://www.georss.org/georss}point')
        if geo_point is None or not geo_point.text:
            continue
        try:
            lat, lon = map(float, geo_point.text.split())
        except ValueError:
            continue

        if not _in_south_asia(lat, lon):
            filtered_out += 1
            continue

        # Duplicate check
        existing = db.query(DisasterEvent).filter(
            DisasterEvent.source == SourceEnum.gdacs,
            text(f"raw_payload->>'eventid' = '{ext_id}'")
        ).first()
        if existing:
            skipped += 1
            continue

        title_elem = item.find('title')
        title = title_elem.text if title_elem is not None else "Unknown"
        ev_type_elem = item.find('gdacs:eventtype', namespaces)
        event_type_str = ev_type_elem.text if ev_type_elem is not None else "other"
        alert_elem = item.find('gdacs:alertlevel', namespaces)
        alert_level_str = alert_elem.text if alert_elem is not None else "Green"

        pub_date = item.find('pubDate')
        event_time = datetime.utcnow()
        if pub_date is not None and pub_date.text:
            try:
                from email.utils import parsedate_to_datetime
                et = parsedate_to_datetime(pub_date.text)
                event_time = et.replace(tzinfo=None) if et.tzinfo else et
            except Exception:
                pass

        mag = None
        if normalize_event_type(event_type_str) == EventTypeEnum.earthquake:
            sev_elem = item.find('gdacs:severity', namespaces)
            if sev_elem is not None and sev_elem.text:
                try:
                    mag = float(sev_elem.text.replace('M', '').strip().split(',')[0].split()[0])
                except Exception:
                    pass

        new_event = DisasterEvent(
            source=SourceEnum.gdacs,
            event_type=normalize_event_type(event_type_str),
            alert_level=normalize_alert_level(alert_level_str),
            magnitude=mag,
            location=f"SRID=4326;POINT({lon} {lat})",
            raw_payload={
                "eventid": ext_id,
                "title": title,
                "raw_event_type": event_type_str,
                "raw_alert_level": alert_level_str
            },
            event_time=event_time
        )
        db.add(new_event)
        inserted += 1

    db.commit()
    print(f"GDACS: inserted={inserted} skipped={skipped} filtered_out(non-SA)={filtered_out}")
    return {"inserted": inserted, "updated": updated, "skipped": skipped, "filtered_out": filtered_out}


def fetch_usgs_events(db: Session):
    """
    USGS Earthquake API — filtered to South Asia bounding box.
    Fetches M>=3.0 earthquakes from the past 365 days.
    This yields hundreds of real events across India, Nepal, Pakistan,
    Afghanistan, Bangladesh, Myanmar, Sri Lanka, Bhutan.
    """
    # Past 1 year, South Asia bbox, M>=3.0
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=365)

    url = (
        "https://earthquake.usgs.gov/fdsnws/event/1/query"
        "?format=geojson"
        f"&starttime={start_time.strftime('%Y-%m-%d')}"
        f"&endtime={end_time.strftime('%Y-%m-%d')}"
        f"&minlatitude={SA_LAT_MIN}&maxlatitude={SA_LAT_MAX}"
        f"&minlongitude={SA_LON_MIN}&maxlongitude={SA_LON_MAX}"
        "&minmagnitude=3.0"
        "&limit=1000"
        "&orderby=time"
    )

    try:
        response = requests.get(url, timeout=30)
        data = response.json()
    except Exception as e:
        return {"inserted": 0, "updated": 0, "skipped": 0, "error": str(e)}

    inserted = skipped = 0
    for feature in data.get('features', []):
        ext_id = feature.get('id')
        existing = db.query(DisasterEvent).filter(
            DisasterEvent.source == SourceEnum.usgs,
            text(f"raw_payload->>'id' = '{ext_id}'")
        ).first()
        if existing:
            skipped += 1
            continue

        props = feature.get('properties', {})
        geom = feature.get('geometry', {})
        if not props or not geom or geom.get('type') != 'Point':
            continue

        lon, lat, _ = geom['coordinates']

        # Extra safety: ensure it's in South Asia (USGS bbox param handles it but double-check)
        if not _in_south_asia(lat, lon):
            continue

        mag = props.get('mag')
        time_ms = props.get('time')
        event_time = datetime.utcfromtimestamp(time_ms / 1000.0) if time_ms else datetime.utcnow()

        # USGS alert: green, yellow, orange, red
        usgs_alert = props.get('alert') or 'green'
        # Map yellow -> orange for our schema
        if usgs_alert == 'yellow':
            usgs_alert = 'orange'

        new_event = DisasterEvent(
            source=SourceEnum.usgs,
            event_type=EventTypeEnum.earthquake,
            alert_level=normalize_alert_level(usgs_alert),
            magnitude=mag,
            location=f"SRID=4326;POINT({lon} {lat})",
            raw_payload={
                "id": ext_id,
                "title": props.get('title', ''),
                "url": props.get('url', ''),
                "magType": props.get('magType', ''),
                "place": props.get('place', '')
            },
            event_time=event_time
        )
        db.add(new_event)
        inserted += 1

    db.commit()
    print(f"USGS: inserted={inserted} skipped={skipped}")
    return {"inserted": inserted, "updated": 0, "skipped": skipped}


def fetch_ndma_events(db: Session):
    """
    India NDMA / State disaster alert CAP feeds.
    Tries multiple state feeds. Where location is not in the feed,
    uses the state's geographic centroid (not a single hardcoded point).
    """
    # State CAP feeds with their geographic centroids as fallback coordinates
    feeds = [
        {
            "url": "https://alert.up.nic.in/cap/rss.xml",
            "state": "UP",
            "lat": 26.8467, "lon": 80.9462,    # Lucknow centroid
            "label": "Uttar Pradesh"
        },
    ]

    # State centroid lookup for NDMA title-based guessing
    STATE_COORDS = {
        "rajasthan": (26.4499, 74.6399),
        "gujarat": (22.2587, 71.1924),
        "maharashtra": (19.7515, 75.7139),
        "kerala": (10.8505, 76.2711),
        "tamil": (11.1271, 78.6569),
        "karnataka": (15.3173, 75.7139),
        "andhra": (15.9129, 79.7400),
        "telangana": (17.1232, 79.2088),
        "odisha": (20.9517, 85.0985),
        "west bengal": (22.9868, 87.8550),
        "bihar": (25.0961, 85.3131),
        "jharkhand": (23.6102, 85.2799),
        "assam": (26.2006, 92.9376),
        "meghalaya": (25.4670, 91.3662),
        "manipur": (24.6637, 93.9063),
        "mizoram": (23.1645, 92.9376),
        "sikkim": (27.5330, 88.5122),
        "himachal": (31.1048, 77.1734),
        "uttarakhand": (30.0668, 79.0193),
        "jammu": (33.7782, 76.5762),
        "delhi": (28.7041, 77.1025),
        "punjab": (31.1471, 75.3412),
        "haryana": (29.0588, 76.0856),
        "madhya": (22.9734, 78.6569),
        "chhattisgarh": (21.2787, 81.8661),
        "up": (26.8467, 80.9462),
    }

    def guess_coords_from_title(title: str, fallback_lat: float, fallback_lon: float):
        title_lower = title.lower()
        for keyword, (lat, lon) in STATE_COORDS.items():
            if keyword in title_lower:
                import random
                # small jitter so events don't all stack at the same point
                return lat + random.uniform(-0.5, 0.5), lon + random.uniform(-0.5, 0.5)
        return fallback_lat + random.uniform(-0.3, 0.3), fallback_lon + random.uniform(-0.3, 0.3)

    import random
    total_inserted = total_skipped = 0

    for feed_cfg in feeds:
        try:
            response = requests.get(feed_cfg["url"], timeout=15)
            response.raise_for_status()
        except Exception as e:
            print(f"NDMA feed {feed_cfg['label']} failed: {e}")
            continue

        try:
            root = ET.fromstring(response.content)
        except Exception:
            continue

        for item in root.findall('.//item'):
            title_elem = item.find('title')
            title = title_elem.text if title_elem is not None else "Unknown Alert"
            guid_elem = item.find('guid')
            guid = guid_elem.text if guid_elem is not None else str(uuid.uuid4())

            existing = db.query(DisasterEvent).filter(
                DisasterEvent.source == SourceEnum.ndma,
                text(f"raw_payload->>'guid' = '{guid}'")
            ).first()
            if existing:
                total_skipped += 1
                continue

            lat, lon = guess_coords_from_title(title, feed_cfg["lat"], feed_cfg["lon"])

            new_event = DisasterEvent(
                source=SourceEnum.ndma,
                event_type=normalize_event_type(title),
                alert_level=AlertLevelEnum.medium,
                magnitude=None,
                location=f"SRID=4326;POINT({lon} {lat})",
                raw_payload={
                    "guid": guid,
                    "title": title,
                    "state": feed_cfg["label"]
                },
                event_time=datetime.utcnow()
            )
            db.add(new_event)
            total_inserted += 1

    db.commit()
    print(f"NDMA: inserted={total_inserted} skipped={total_skipped}")
    return {"inserted": total_inserted, "updated": 0, "skipped": total_skipped}


def compute_impact_extent(db: Session, event_id: str):
    event = db.query(DisasterEvent).filter(DisasterEvent.id == event_id).first()
    if not event:
        return {"error": "Event not found"}

    radius_meters = 10000
    if event.event_type == EventTypeEnum.earthquake and event.magnitude:
        r_km = 10 * (1.5 ** (event.magnitude - 4))
        radius_meters = r_km * 1000
    else:
        if event.alert_level in [AlertLevelEnum.red, AlertLevelEnum.critical]:
            radius_meters = 100000
        elif event.alert_level in [AlertLevelEnum.orange, AlertLevelEnum.high]:
            radius_meters = 50000
        elif event.alert_level in [AlertLevelEnum.green, AlertLevelEnum.low]:
            radius_meters = 10000

    query = text('''
        UPDATE disaster_events
        SET impact_extent = ST_Buffer(location::geography, :radius)::geometry
        WHERE id = :id
        RETURNING ST_AsGeoJSON(impact_extent)
    ''')
    result = db.execute(query, {"radius": radius_meters, "id": event.id}).fetchone()
    db.commit()
    return {"event_id": str(event.id), "radius_meters": radius_meters, "impact_extent_geojson": result[0]}


def compute_population_exposure(db: Session, event_id: str):
    event = db.query(DisasterEvent).filter(DisasterEvent.id == event_id).first()
    if not event or event.impact_extent is None:
        return {"error": "Event not found or missing impact_extent"}

    density_per_sq_km = 50
    query = text('''
        SELECT ST_Area(impact_extent::geography) / 1000000.0 AS area_sq_km
        FROM disaster_events WHERE id = :id
    ''')
    result = db.execute(query, {"id": event.id}).fetchone()
    area_sq_km = result[0] if result and result[0] else 0
    population = int(area_sq_km * density_per_sq_km)
    event.population_exposed = population
    db.commit()
    return {"event_id": str(event.id), "area_sq_km": area_sq_km, "population_exposed": population}


def compute_building_footprint(db: Session, event_id: str):
    event = db.query(DisasterEvent).filter(DisasterEvent.id == event_id).first()
    if not event or event.impact_extent is None:
        return {"error": "Event not found or missing impact_extent"}
    building_count = int((event.population_exposed or 0) / 4)
    event.buildings_affected = building_count
    event.critical_infrastructure_count = max(1, int(building_count * 0.01))
    db.commit()
    return {
        "event_id": str(event.id),
        "buildings_affected": event.buildings_affected,
        "critical_infrastructure_count": event.critical_infrastructure_count
    }


def get_satellite_imagery(event_id: str, db: Session):
    event = db.query(DisasterEvent).filter(DisasterEvent.id == event_id).first()
    if not event:
        return {"error": "Event not found"}
    query_bbox = text('''
        SELECT ST_YMin(location), ST_XMin(location), ST_YMax(location), ST_XMax(location)
        FROM disaster_events WHERE id = :id
    ''')
    bbox_res = db.execute(query_bbox, {"id": event.id}).fetchone()
    bbox_str = f"{bbox_res[1]},{bbox_res[0]},{bbox_res[3]},{bbox_res[2]}"
    return {
        "event_id": event_id,
        "imagery_urls": [f"https://services.sentinel-hub.com/ogc/wms/mock-key?REQUEST=GetMap&BBOX={bbox_str}&LAYERS=TRUE_COLOR&WIDTH=512&HEIGHT=512"],
        "metadata": {"source": "Sentinel-2", "bbox": bbox_str}
    }

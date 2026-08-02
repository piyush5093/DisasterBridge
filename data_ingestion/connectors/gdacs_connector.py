"""
GDACS API Connector
Fetches real-time global disaster events from GDACS (Global Disaster Alert and Coordination System)
API Docs: https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH
"""

import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings


class GDACSConnector:
    BASE_URL = settings.GDACS_API_URL

    def fetch_events(
        self,
        event_type: Optional[str] = None,     # FL, EQ, TC, LS, DR
        alert_level: Optional[str] = None,    # green, orange, red
        country: str = "IND",                 # ISO3 country code for India
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Fetch latest disaster events from GDACS API.
        Returns a list of event dicts.
        """
        params: Dict[str, Any] = {
            "alertlevel": alert_level or "Orange,Red",
            "country":    country,
            "limit":      limit,
        }
        if event_type:
            params["eventtype"] = event_type

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(
                    self.BASE_URL,
                    params=params,
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                data = response.json()

                # GDACS returns {"features": [...]} or {"result": [...]}
                if isinstance(data, dict):
                    events = data.get("features", data.get("result", []))
                elif isinstance(data, list):
                    events = data
                else:
                    events = []

                # Flatten properties from GeoJSON features if needed
                normalized = []
                for item in events:
                    if "properties" in item:
                        props = item["properties"]
                        coords = item.get("geometry", {}).get("coordinates", [0, 0])
                        props["longitude"] = coords[0] if len(coords) > 0 else 0
                        props["latitude"]  = coords[1] if len(coords) > 1 else 0
                        normalized.append(props)
                    else:
                        normalized.append(item)

                print(f"[GDACS] Fetched {len(normalized)} events (country={country})")
                return normalized

        except httpx.HTTPStatusError as e:
            print(f"[GDACS] HTTP error: {e.response.status_code} — {e.response.text}")
            return []
        except Exception as e:
            print(f"[GDACS] Connection error: {e}")
            return []

    def fetch_all_india(self) -> List[Dict[str, Any]]:
        """Fetch all active events for India across all disaster types."""
        return self.fetch_events(country="IND", limit=100)

    def fetch_floods_india(self) -> List[Dict[str, Any]]:
        return self.fetch_events(event_type="FL", country="IND")

    def fetch_earthquakes_india(self) -> List[Dict[str, Any]]:
        return self.fetch_events(event_type="EQ", country="IND")

    def fetch_cyclones_india(self) -> List[Dict[str, Any]]:
        return self.fetch_events(event_type="TC", country="IND")


# Singleton instance
gdacs = GDACSConnector()

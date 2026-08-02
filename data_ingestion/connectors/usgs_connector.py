"""
USGS Earthquake API Connector
Fetches real-time earthquake data for India region
API Docs: https://earthquake.usgs.gov/fdsnws/event/1/
"""

import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.core.config import settings


# India bounding box (approximate)
INDIA_BBOX = {
    "minlatitude":  8.0,
    "maxlatitude":  37.0,
    "minlongitude": 68.0,
    "maxlongitude": 97.5,
}


class USGSConnector:
    BASE_URL = settings.USGS_API_URL

    def fetch_earthquakes(
        self,
        min_magnitude: float = 4.0,
        days_back: int = 7,
        limit: int = 50,
        bbox: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent earthquakes from USGS for India region.
        Returns GeoJSON feature list.
        """
        end_time   = datetime.utcnow()
        start_time = end_time - timedelta(days=days_back)

        region = bbox or INDIA_BBOX

        params: Dict[str, Any] = {
            "format":       "geojson",
            "starttime":    start_time.strftime("%Y-%m-%d"),
            "endtime":      end_time.strftime("%Y-%m-%d"),
            "minmagnitude": min_magnitude,
            "limit":        limit,
            "orderby":      "magnitude",
            **region,
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data     = response.json()
                features = data.get("features", [])
                print(f"[USGS] Fetched {len(features)} earthquakes (M≥{min_magnitude}, last {days_back} days)")
                return features

        except httpx.HTTPStatusError as e:
            print(f"[USGS] HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            print(f"[USGS] Connection error: {e}")
            return []

    def fetch_significant(self) -> List[Dict[str, Any]]:
        """Fetch M≥5.0 earthquakes in India in last 30 days."""
        return self.fetch_earthquakes(min_magnitude=5.0, days_back=30)

    def fetch_recent(self) -> List[Dict[str, Any]]:
        """Fetch M≥4.0 earthquakes in India in last 7 days."""
        return self.fetch_earthquakes(min_magnitude=4.0, days_back=7)

    def get_summary(self, features: List[Dict]) -> Dict[str, Any]:
        """Return summary stats for a list of USGS features."""
        if not features:
            return {"count": 0, "max_magnitude": 0, "avg_magnitude": 0}
        mags = [f["properties"].get("mag", 0) for f in features if f.get("properties")]
        return {
            "count":         len(features),
            "max_magnitude": round(max(mags), 1) if mags else 0,
            "avg_magnitude": round(sum(mags) / len(mags), 2) if mags else 0,
        }


# Singleton instance
usgs = USGSConnector()

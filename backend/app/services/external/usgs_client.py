"""
USGS Earthquake Hazards Program API client.

Endpoints (confirmed against USGS's FDSN documentation and a live schema
check on 2026-07-24 — see the property list in usgs_ingestion.py, which
matches exactly: mag, place, time, updated, tz, url, detail, felt, cdi,
mmi, alert, status, tsunami, sig, net, code, ids, sources, types, nst,
dmin, rms, gap, magType, type, title):

- FDSN query: https://earthquake.usgs.gov/fdsnws/event/1/query
  format=geojson, filterable by starttime/endtime (ISO-8601),
  minmagnitude/maxmagnitude, bounding box (minlatitude/maxlatitude/
  minlongitude/maxlongitude) or radius (latitude/longitude/maxradiuskm).
  Capped at 20,000 features per response; use `limit`/`offset` to
  paginate for very large pulls (not needed at our current scale).

- Real-time summary feeds: https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/{feed}.geojson
  Pre-computed, cached feeds USGS recommends over ad-hoc queries for
  "what's happening right now" use cases (lower latency, no query cost).
  {feed} is one of: significant, 4.5, 2.5, 1.0, all — each combined with
  a window: _hour, _day, _week, _month (e.g. "significant_week").
"""

from datetime import date
from typing import Any

import httpx

from app.core.config import settings

DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)


class USGSClientError(Exception):
    """Raised when the USGS API returns an error or an unparseable response."""


class USGSClient:
    def __init__(self, base_url: str | None = None, timeout: httpx.Timeout = DEFAULT_TIMEOUT):
        self.base_url = (base_url or settings.USGS_EARTHQUAKE_API_BASE).rstrip("/")
        self._timeout = timeout

    async def _get(self, url: str, params: dict[str, Any] | None = None) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise USGSClientError(
                    f"USGS API returned {exc.response.status_code} for {exc.request.url}"
                ) from exc
            except httpx.RequestError as exc:
                raise USGSClientError(f"USGS API request failed: {exc}") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise USGSClientError("USGS API returned a non-JSON response") from exc

    async def query_earthquakes(
        self,
        start_time: date | None = None,
        end_time: date | None = None,
        min_magnitude: float | None = None,
        max_magnitude: float | None = None,
        min_latitude: float | None = None,
        max_latitude: float | None = None,
        min_longitude: float | None = None,
        max_longitude: float | None = None,
        limit: int = 500,
    ) -> dict:
        """
        Custom-filtered pull via the FDSN `query` method. Any combination
        of filters may be omitted — USGS defaults to a wide, recent window
        if nothing is specified, so callers should generally at least pass
        `min_magnitude` and a time range to keep responses small.
        """
        params: dict[str, Any] = {"format": "geojson", "limit": limit, "orderby": "time"}
        if start_time:
            params["starttime"] = start_time.isoformat()
        if end_time:
            params["endtime"] = end_time.isoformat()
        if min_magnitude is not None:
            params["minmagnitude"] = min_magnitude
        if max_magnitude is not None:
            params["maxmagnitude"] = max_magnitude
        if min_latitude is not None:
            params["minlatitude"] = min_latitude
        if max_latitude is not None:
            params["maxlatitude"] = max_latitude
        if min_longitude is not None:
            params["minlongitude"] = min_longitude
        if max_longitude is not None:
            params["maxlongitude"] = max_longitude

        return await self._get(f"{self.base_url}/query", params=params)

    async def get_summary_feed(self, feed: str = "significant_week") -> dict:
        """
        Pull a pre-computed real-time summary feed.

        feed: "<magnitude>_<window>" — magnitude is one of
        significant|4.5|2.5|1.0|all, window is one of hour|day|week|month.
        E.g. "4.5_day" = all M4.5+ earthquakes in the last 24 hours,
        "significant_month" = all significant earthquakes in the last month.
        """
        url = f"https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/{feed}.geojson"
        return await self._get(url)

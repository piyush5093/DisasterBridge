"""
Overpass API client — pulls OpenStreetMap building footprints for a
bounding box.

CONFIRMED via OSM's own wiki/community docs (2026-07-27): POSTing
`data=<Overpass QL query>` to https://overpass-api.de/api/interpreter
with `[out:json]` and `out geom;` returns each matched way's node
coordinates inline as a `geometry: [{lat, lon}, ...]` array — no need
to separately resolve node references, which is what most older
tutorials' `(._;>;); out;` pattern does the hard way. Response shape:
    {"elements": [
        {"type": "way", "id": ..., "bounds": {...}, "nodes": [...],
         "geometry": [{"lat":.., "lon":..}, ...], "tags": {"building": "yes", ...}},
        {"type": "node", "id": ..., "lat":.., "lon":.., "tags": {...}}  # standalone building=* nodes
    ]}
"""

import httpx

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)


class OverpassClientError(Exception):
    """Raised when the Overpass API returns an error or an unparseable response."""


class OverpassClient:
    def __init__(self, base_url: str = OVERPASS_URL, timeout: httpx.Timeout = DEFAULT_TIMEOUT):
        self.base_url = base_url
        self._timeout = timeout

    async def get_building_footprints(
        self,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        query_timeout_s: int = 25,
    ) -> dict:
        """
        Fetch building footprints (ways and standalone nodes tagged
        building=*) within a bounding box. Overpass bbox order is
        (south, west, north, east) = (min_lat, min_lon, max_lat, max_lon)
        — different axis order from GeoJSON/most of this project's other
        clients, easy to transpose by accident, called out here.
        """
        query = (
            f"[out:json][timeout:{query_timeout_s}];"
            f"("
            f'way["building"]({min_lat},{min_lon},{max_lat},{max_lon});'
            f'node["building"]({min_lat},{min_lon},{max_lat},{max_lon});'
            f");"
            f"out geom;"
        )

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(self.base_url, data={"data": query})
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise OverpassClientError(
                    f"Overpass API returned {exc.response.status_code}: {exc.response.text[:300]}"
                ) from exc
            except httpx.RequestError as exc:
                raise OverpassClientError(f"Overpass API request failed: {exc}") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise OverpassClientError("Overpass API returned a non-JSON response") from exc

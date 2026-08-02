"""
Satellite imagery client for damage/flood-extent visualization, via the
Copernicus Data Space Ecosystem (CDSE) — the platform Sentinel Hub
migrated to.

⚠️ ENDPOINT MIGRATION (confirmed live 2026-07-24): the old
`services.sentinel-hub.com` OAuth/API endpoints referenced in a lot of
older Sentinel Hub tutorials are deprecated post-migration. Current,
confirmed endpoints:
  - Token:   https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token
  - Process API base: https://sh.dataspace.copernicus.eu
CDSE also announced (2026-03-09) a parallel new path format rolling out
from March 17, 2026 (`/process/v1` alongside the legacy `/api/v1/process`
— both work, legacy is not yet deprecated). This client uses the new
`/process/v1` form since CDSE's own response links now point to it.

Auth: OAuth2 client-credentials grant. Register an OAuth client in the
CDSE/Sentinel Hub dashboard to get SENTINEL_HUB_CLIENT_ID/SECRET
(see .env.example) — this client cannot work without those credentials
configured, same as GDACS/USGS need no auth but this API does.

Scope for Day 4: fetch imagery for a bounding box + date, either as
true-color (visual reference) or NDWI (Normalized Difference Water
Index — the standard band-math for flood/water extent from optical
imagery). Persisting these into the DB as proper raster data (rather
than returning PNG bytes for direct display) is scoped for Week 1 Day 6
("Geospatial impact module: flood/earthquake extent maps"), which is
where rasterio/geopandas get wired in per the project's stated stack.
"""

import time
from typing import Any

import httpx

from app.core.config import settings

TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
PROCESS_API_URL = "https://sh.dataspace.copernicus.eu/process/v1"

DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)

# Standard true-color visualization (bands B04/B03/B02 = R/G/B).
TRUE_COLOR_EVALSCRIPT = """
//VERSION=3
function setup() {
  return { input: ["B02", "B03", "B04"], output: { bands: 3 } };
}
function evaluatePixel(sample) {
  return [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02];
}
"""

# NDWI = (Green - NIR) / (Green + NIR), the standard water/flood index
# for Sentinel-2 (B03=green, B08=NIR). Rendered as a blue-scale mask so
# water/flooded areas show up clearly against dry land (near-zero/negative).
NDWI_EVALSCRIPT = """
//VERSION=3
function setup() {
  return { input: ["B03", "B08"], output: { bands: 3 } };
}
function evaluatePixel(sample) {
  let ndwi = (sample.B03 - sample.B08) / (sample.B03 + sample.B08 + 1e-6);
  let water = Math.max(0, Math.min(1, (ndwi + 0.2) / 0.6));
  return [0, water * 0.4, water];
}
"""


class SentinelHubClientError(Exception):
    """Raised when auth fails or the Process API returns an error."""


class SentinelHubClient:
    """
    Caches its own OAuth2 access token in-memory (tokens last ~1 hour
    per CDSE docs); reuse one instance across requests rather than
    creating a new one per call so the token isn't re-fetched every time.
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
    ):
        self.client_id = client_id or settings.SENTINEL_HUB_CLIENT_ID
        self.client_secret = client_secret or settings.SENTINEL_HUB_CLIENT_SECRET
        self._timeout = timeout
        self._access_token: str | None = None
        self._token_expiry: float = 0.0

    async def _get_access_token(self) -> str:
        if self._access_token and time.time() < self._token_expiry - 30:
            return self._access_token

        if not self.client_id or not self.client_secret:
            raise SentinelHubClientError(
                "SENTINEL_HUB_CLIENT_ID/SENTINEL_HUB_CLIENT_SECRET are not configured. "
                "Register an OAuth client at https://shapps.dataspace.copernicus.eu/dashboard/#/ "
                "and set them in .env."
            )

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(
                    TOKEN_URL,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise SentinelHubClientError(
                    f"CDSE token request failed ({exc.response.status_code}): {exc.response.text}"
                ) from exc
            except httpx.RequestError as exc:
                raise SentinelHubClientError(f"CDSE token request failed: {exc}") from exc

        token_data = response.json()
        self._access_token = token_data["access_token"]
        self._token_expiry = time.time() + token_data.get("expires_in", 3600)
        return self._access_token

    async def _process_request(self, payload: dict[str, Any]) -> bytes:
        token = await self._get_access_token()

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(
                    PROCESS_API_URL,
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise SentinelHubClientError(
                    f"Sentinel Hub Process API returned {exc.response.status_code}: {exc.response.text}"
                ) from exc
            except httpx.RequestError as exc:
                raise SentinelHubClientError(f"Sentinel Hub Process API request failed: {exc}") from exc

        return response.content

    def _build_payload(
        self,
        bbox: tuple[float, float, float, float],
        time_from: str,
        time_to: str,
        evalscript: str,
        width: int,
        height: int,
    ) -> dict[str, Any]:
        return {
            "input": {
                "bounds": {
                    "bbox": list(bbox),  # [min_lon, min_lat, max_lon, max_lat], WGS84
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
                },
                "data": [
                    {
                        "type": "sentinel-2-l2a",
                        "dataFilter": {
                            "timeRange": {"from": f"{time_from}T00:00:00Z", "to": f"{time_to}T23:59:59Z"},
                            "mosaickingOrder": "leastCC",  # prefer least-cloudy scene in range
                        },
                    }
                ],
            },
            "output": {
                "width": width,
                "height": height,
                "responses": [{"identifier": "default", "format": {"type": "image/png"}}],
            },
            "evalscript": evalscript,
        }

    async def get_true_color_image(
        self,
        bbox: tuple[float, float, float, float],
        time_from: str,
        time_to: str,
        width: int = 512,
        height: int = 512,
    ) -> bytes:
        """True-color PNG for a bounding box + date range — visual reference imagery."""
        payload = self._build_payload(bbox, time_from, time_to, TRUE_COLOR_EVALSCRIPT, width, height)
        return await self._process_request(payload)

    async def get_flood_extent_image(
        self,
        bbox: tuple[float, float, float, float],
        time_from: str,
        time_to: str,
        width: int = 512,
        height: int = 512,
    ) -> bytes:
        """NDWI-based water/flood-extent PNG for a bounding box + date range."""
        payload = self._build_payload(bbox, time_from, time_to, NDWI_EVALSCRIPT, width, height)
        return await self._process_request(payload)

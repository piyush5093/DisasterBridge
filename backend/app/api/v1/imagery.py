"""
Satellite imagery endpoints — true-color reference and NDWI-based
flood/water-extent imagery over a bounding box + date range, via
Sentinel Hub / Copernicus Data Space Ecosystem (see sentinel_hub_client.py
for the endpoint-migration notes and evalscript details).

Returns raw PNG bytes directly (StreamingResponse) rather than persisting
to the DB — see sentinel_hub_client.py's module docstring for why
DB/raster persistence is scoped to Week 1 Day 6 instead.
"""

import io

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.services.external.sentinel_hub_client import SentinelHubClient, SentinelHubClientError

router = APIRouter(prefix="/imagery/sentinel", tags=["imagery"])

_client = SentinelHubClient()


@router.get("/true-color")
async def true_color_image(
    min_lon: float = Query(...),
    min_lat: float = Query(...),
    max_lon: float = Query(...),
    max_lat: float = Query(...),
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    width: int = Query(512, le=2048),
    height: int = Query(512, le=2048),
) -> StreamingResponse:
    try:
        png_bytes = await _client.get_true_color_image(
            bbox=(min_lon, min_lat, max_lon, max_lat),
            time_from=from_date,
            time_to=to_date,
            width=width,
            height=height,
        )
    except SentinelHubClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return StreamingResponse(io.BytesIO(png_bytes), media_type="image/png")


@router.get("/flood-extent")
async def flood_extent_image(
    min_lon: float = Query(...),
    min_lat: float = Query(...),
    max_lon: float = Query(...),
    max_lat: float = Query(...),
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    width: int = Query(512, le=2048),
    height: int = Query(512, le=2048),
) -> StreamingResponse:
    try:
        png_bytes = await _client.get_flood_extent_image(
            bbox=(min_lon, min_lat, max_lon, max_lat),
            time_from=from_date,
            time_to=to_date,
            width=width,
            height=height,
        )
    except SentinelHubClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return StreamingResponse(io.BytesIO(png_bytes), media_type="image/png")

"""
Population-in-polygon estimation from a population-density raster
(GeoTIFF), via rasterio zonal statistics (mask the raster to the
polygon, sum the pixel values inside it).

⚠️ DATA SOURCE — honest note on scope: this service computes correctly
against ANY population-count GeoTIFF (each pixel = estimated people in
that cell, the standard format for this kind of data), but does not
itself download one. WorldPop (https://www.worldpop.org) publishes
free, ~100m-resolution population-count rasters per country via a
public API — but worldpop.org is outside this sandbox's allowed network
domains, so an actual download couldn't be verified live here the way
GDACS/USGS/NDMA were. To use this for real:
  1. Download a WorldPop country GeoTIFF (e.g. constrained individual
     countries 2020 UN-adjusted, "ppp" = population per pixel) from
     https://hub.worldpop.org/geodata/summary?id=49730-style pages, or
     via their REST API (see WorldPop's own API docs).
  2. Point `POPULATION_RASTER_PATH` at the downloaded file.
This module's correctness is verified in tests against a small
synthetic raster built with rasterio itself (tests/test_population_density.py)
rather than a real WorldPop file, since one isn't available in this
environment — the zonal-statistics logic is identical either way.
"""

from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.mask import mask as rasterio_mask


class PopulationRasterError(Exception):
    """Raised when the configured raster is missing or unreadable."""


def estimate_population_in_polygon(raster_path: str | Path, polygon_geojson: dict[str, Any]) -> dict[str, Any]:
    """
    Sum population-count pixel values that fall inside `polygon_geojson`
    (a GeoJSON Polygon, e.g. from app/services/impact/extent_calculator.py).

    Returns a dict with the total estimate plus enough metadata to sanity
    -check it (pixel count, nodata handling) rather than just a bare number.
    """
    path = Path(raster_path)
    if not path.exists():
        raise PopulationRasterError(
            f"Population raster not found at {path}. See module docstring for how to obtain one (WorldPop)."
        )

    try:
        with rasterio.open(path) as src:
            nodata = src.nodata
            out_image, _out_transform = rasterio_mask(src, [polygon_geojson], crop=True, nodata=nodata)
    except ValueError as exc:
        # rasterio.mask raises ValueError if the polygon doesn't overlap the raster at all.
        return {
            "estimated_population": 0,
            "pixel_count": 0,
            "note": f"Polygon does not overlap raster extent: {exc}",
        }
    except rasterio.errors.RasterioIOError as exc:
        raise PopulationRasterError(f"Failed to read raster at {path}: {exc}") from exc

    band = out_image[0].astype("float64")

    if nodata is not None:
        valid_mask = band != nodata
    else:
        valid_mask = ~np.isnan(band)

    # Population rasters shouldn't have negative counts — guard against
    # stray negative nodata sentinels that weren't caught by `nodata` above.
    valid_mask &= band >= 0

    total_population = float(band[valid_mask].sum())
    pixel_count = int(valid_mask.sum())

    return {
        "estimated_population": round(total_population),
        "pixel_count": pixel_count,
        "note": None,
    }

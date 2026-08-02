"""
Tests for app/services/population/density_service.py.

Uses a small SYNTHETIC raster built with rasterio (not a real WorldPop
file — see density_service.py's docstring for why one isn't available
in this environment). This still genuinely exercises the zonal-stats
math: a raster with known, hand-picked pixel values is written to disk,
then masked against a polygon whose expected covered pixels are known
in advance, so the assertions check real computed sums rather than
just "returns something".
"""

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from app.services.population.density_service import PopulationRasterError, estimate_population_in_polygon


@pytest.fixture
def synthetic_raster(tmp_path):
    """
    Builds a 10x10 pixel raster, each pixel = 1 degree x 1 degree,
    covering lon [0,10], lat [0,10] (north-up, so row 0 = top = lat 10).
    Every pixel is set to a known population value of 100, except a
    5x5 block in the top-left (lon 0-5, lat 5-10) set to 500, and one
    nodata pixel at (0,0)-(1,1) to test nodata handling.
    """
    path = tmp_path / "synthetic_population.tif"
    data = np.full((10, 10), 100.0, dtype="float64")
    data[0:5, 0:5] = 500.0  # top-left block: lon 0-5, lat 5-10 (rows 0-4)
    data[9, 9] = -99999.0  # nodata sentinel at bottom-right corner pixel

    transform = from_origin(west=0, north=10, xsize=1, ysize=1)

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype="float64",
        crs="EPSG:4326",
        transform=transform,
        nodata=-99999.0,
    ) as dst:
        dst.write(data, 1)

    return path


def test_estimates_population_for_uniform_region(synthetic_raster):
    # A 2x2 degree polygon entirely within the "100 per pixel" region
    # (lon 6-8, lat 1-3) covers exactly 4 pixels -> 400 total.
    polygon = {
        "type": "Polygon",
        "coordinates": [[[6, 1], [8, 1], [8, 3], [6, 3], [6, 1]]],
    }

    result = estimate_population_in_polygon(synthetic_raster, polygon)

    assert result["estimated_population"] == 400
    assert result["pixel_count"] == 4


def test_estimates_population_for_high_density_block(synthetic_raster):
    # A polygon inside the 500-per-pixel block (lon 1-3, lat 6-8) -> 4 pixels * 500 = 2000.
    polygon = {
        "type": "Polygon",
        "coordinates": [[[1, 6], [3, 6], [3, 8], [1, 8], [1, 6]]],
    }

    result = estimate_population_in_polygon(synthetic_raster, polygon)

    assert result["estimated_population"] == 2000


def test_polygon_outside_raster_extent_returns_zero(synthetic_raster):
    polygon = {
        "type": "Polygon",
        "coordinates": [[[100, 100], [101, 100], [101, 101], [100, 101], [100, 100]]],
    }

    result = estimate_population_in_polygon(synthetic_raster, polygon)

    assert result["estimated_population"] == 0
    assert result["note"] is not None


def test_missing_raster_file_raises_clear_error(tmp_path):
    missing_path = tmp_path / "does_not_exist.tif"
    polygon = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}

    with pytest.raises(PopulationRasterError, match="not found"):
        estimate_population_in_polygon(missing_path, polygon)

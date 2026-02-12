"""
Compute terrain derivatives from a Digital Elevation Model (DEM).

Generates slope (degrees) and Terrain Ruggedness Index (TRI) rasters
using GDAL's DEMProcessing. Both outputs preserve the input CRS,
resolution, and extent.

References:
    - Riley, S.J., DeGloria, S.D., Elliot, R. (1999). A terrain ruggedness
      index that quantifies topographic heterogeneity.
    - Wilson, M.F.J., et al. (2007). Multiscale terrain analysis of
      multibeam bathymetry data for habitat mapping.

Usage:
    python compute_terrain_derivatives.py
    python compute_terrain_derivatives.py --input /path/to/dem.tif --output-dir /path/to/output/
"""

import os
import argparse
import logging
from osgeo import gdal

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Project root (two levels up from src/preprocessing/)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Default paths
DEFAULT_INPUT = os.path.join(PROJECT_ROOT, "data", "processed", "rasters", "dem.tif")
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "processed", "rasters")

GTIFF_OPTIONS = ["COMPRESS=LZW", "TILED=YES", "PREDICTOR=2"]


def compute_slope(input_path: str, output_path: str) -> None:
    """Compute slope in degrees from a DEM raster."""
    logger.info("Computing slope: %s", output_path)
    ds = gdal.Open(input_path)
    if ds is None:
        raise FileNotFoundError(f"Cannot open DEM: {input_path}")

    gdal.DEMProcessing(
        output_path, ds, "slope",
        format="GTiff",
        slopeFormat="degree",
        creationOptions=GTIFF_OPTIONS,
    )
    ds = None
    logger.info("Slope saved: %s", output_path)


def compute_tri(input_path: str, output_path: str) -> None:
    """Compute Terrain Ruggedness Index (TRI) from a DEM raster."""
    logger.info("Computing TRI: %s", output_path)
    ds = gdal.Open(input_path)
    if ds is None:
        raise FileNotFoundError(f"Cannot open DEM: {input_path}")

    gdal.DEMProcessing(
        output_path, ds, "TRI",
        format="GTiff",
        creationOptions=GTIFF_OPTIONS,
    )
    ds = None
    logger.info("TRI saved: %s", output_path)


def main():
    parser = argparse.ArgumentParser(description="Compute terrain derivatives from DEM.")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Path to input DEM raster.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory.")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    slope_path = os.path.join(args.output_dir, "pendiente.tif")
    tri_path = os.path.join(args.output_dir, "rugosidad.tif")

    compute_slope(args.input, slope_path)
    compute_tri(args.input, tri_path)

    logger.info("All derivatives computed successfully.")


if __name__ == "__main__":
    main()
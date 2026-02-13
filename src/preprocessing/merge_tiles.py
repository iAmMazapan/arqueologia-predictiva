"""Merge and reproject ASTER GDEM tiles into a single DEM raster.

Scans data/raw/dem_tiles/ for extracted *_dem.tif files, builds a GDAL
Virtual Raster (VRT) mosaic, and reprojects to South America Albers
Equal Area Conic (ESRI:102033) at 30m resolution.

Output:
    data/processed/rasters/dem.tif

Usage:
    python merge_tiles.py
    python merge_tiles.py --input-dir /path/to/tiles --output /path/to/dem.tif
"""

import os
import glob
import argparse
import logging

from osgeo import gdal

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_INPUT_DIR = os.path.join(PROJECT_ROOT, "data", "raw", "dem_tiles")
DEFAULT_OUTPUT = os.path.join(PROJECT_ROOT, "data", "processed", "rasters", "dem.tif")

TARGET_CRS = "ESRI:102033"  # South America Albers Equal Area Conic
PIXEL_SIZE = 30              # meters

GTIFF_OPTIONS = [
    "COMPRESS=LZW",
    "TILED=YES",
    "BIGTIFF=YES",
    "NUM_THREADS=ALL_CPUS",
    "PREDICTOR=2",
]


def merge_and_reproject(input_dir: str, output_path: str) -> None:
    """Build VRT mosaic from DEM tiles and warp to target CRS."""
    pattern = os.path.join(input_dir, "**", "*dem.tif")
    tiles = [f for f in glob.glob(pattern, recursive=True) if os.path.isfile(f)]

    if not tiles:
        raise FileNotFoundError(f"No *dem.tif files found in {input_dir}")

    logger.info("Found %d DEM tiles in %s", len(tiles), input_dir)

    # Step 1: Virtual mosaic
    vrt_path = output_path.replace(".tif", "_temp.vrt")
    logger.info("Building VRT mosaic ...")
    vrt_opts = gdal.BuildVRTOptions(resampleAlg="cubic", srcNodata=None)
    gdal.BuildVRT(vrt_path, tiles, options=vrt_opts)

    # Step 2: Warp to target CRS and resolution
    logger.info("Warping to %s at %dm resolution ...", TARGET_CRS, PIXEL_SIZE)
    warp_opts = gdal.WarpOptions(
        format="GTiff",
        dstSRS=TARGET_CRS,
        xRes=PIXEL_SIZE,
        yRes=PIXEL_SIZE,
        resampleAlg="bilinear",
        dstNodata=-9999,
        creationOptions=GTIFF_OPTIONS,
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    gdal.Warp(output_path, vrt_path, options=warp_opts)

    # Cleanup
    if os.path.exists(vrt_path):
        os.remove(vrt_path)

    logger.info("DEM saved: %s", output_path)


def main():
    parser = argparse.ArgumentParser(description="Merge and reproject ASTER GDEM tiles.")
    parser.add_argument("--input-dir", default=DEFAULT_INPUT_DIR, help="Directory with DEM tiles.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output DEM path.")
    args = parser.parse_args()
    merge_and_reproject(args.input_dir, args.output)


if __name__ == "__main__":
    main()
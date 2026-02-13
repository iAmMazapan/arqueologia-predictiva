"""Extract DEM tiles from zip archives and merge into a single raster.

This script handles the full pipeline from compressed archives to a
unified DEM: extract *_dem.tif from each .zip, build a virtual mosaic,
and warp to the project CRS (ESRI:102033) at 30m resolution.

Input:  data/raw/dem_tiles/*.zip
Output: data/processed/rasters/dem.tif

Usage:
    python merge_and_reproject_dem.py
    python merge_and_reproject_dem.py --input-dir /path/to/zips --output /path/to/dem.tif
"""

import os
import glob
import zipfile
import argparse
import logging
import shutil

from osgeo import gdal

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_INPUT_DIR = os.path.join(PROJECT_ROOT, "data", "raw", "dem_tiles")
DEFAULT_OUTPUT = os.path.join(PROJECT_ROOT, "data", "processed", "rasters", "dem.tif")

TARGET_CRS = "ESRI:102033"
PIXEL_SIZE = 30

GTIFF_OPTIONS = [
    "COMPRESS=LZW",
    "TILED=YES",
    "BIGTIFF=YES",
    "NUM_THREADS=ALL_CPUS",
    "PREDICTOR=2",
]


def extract_dem_tiles(input_dir: str, temp_dir: str) -> list[str]:
    """Extract *_dem.tif files from zip archives.

    Filters out auxiliary files (*_num.tif, PDFs) to keep only elevation data.
    """
    os.makedirs(temp_dir, exist_ok=True)
    zip_pattern = os.path.join(input_dir, "**", "*.zip")
    zip_files = glob.glob(zip_pattern, recursive=True)
    logger.info("Found %d zip archives.", len(zip_files))

    extracted = []
    for i, zip_path in enumerate(zip_files, 1):
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                for name in zf.namelist():
                    if name.endswith("dem.tif"):
                        zf.extract(name, temp_dir)
                        extracted.append(os.path.join(temp_dir, name))
        except (zipfile.BadZipFile, OSError) as exc:
            logger.warning("Skipping corrupt archive [%d]: %s", i, exc)

    logger.info("Extracted %d DEM tiles.", len(extracted))
    return extracted


def build_mosaic_and_warp(tiles: list[str], output_path: str, temp_dir: str) -> None:
    """Build VRT mosaic and warp to target CRS."""
    if not tiles:
        raise ValueError("No tiles provided for mosaic.")

    vrt_path = os.path.join(temp_dir, "mosaic.vrt")
    logger.info("Building VRT mosaic from %d tiles ...", len(tiles))
    gdal.BuildVRT(vrt_path, tiles, options=gdal.BuildVRTOptions(
        resampleAlg="cubic", srcNodata=None,
    ))

    logger.info("Warping to %s at %dm resolution ...", TARGET_CRS, PIXEL_SIZE)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    gdal.Warp(output_path, vrt_path, options=gdal.WarpOptions(
        format="GTiff",
        dstSRS=TARGET_CRS,
        xRes=PIXEL_SIZE,
        yRes=PIXEL_SIZE,
        resampleAlg="bilinear",
        dstNodata=-9999,
        creationOptions=GTIFF_OPTIONS,
    ))

    logger.info("DEM saved: %s", output_path)


def main():
    parser = argparse.ArgumentParser(description="Extract, merge, and reproject DEM tiles.")
    parser.add_argument("--input-dir", default=DEFAULT_INPUT_DIR, help="Directory with .zip tiles.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output DEM path.")
    args = parser.parse_args()

    temp_dir = os.path.join(args.input_dir, "_temp_extracted")

    try:
        tiles = extract_dem_tiles(args.input_dir, temp_dir)
        build_mosaic_and_warp(tiles, args.output, temp_dir)
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.info("Temporary files cleaned.")


if __name__ == "__main__":
    main()
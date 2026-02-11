"""Generate a preview visualization of the processed DEM raster.

Reads the unified DEM from data/processed/rasters/dem.tif using GDAL
with a downsampling strategy to avoid memory overflow, and saves a
terrain-colored preview image.

Output:
    outputs/figures/dem_preview.png

Usage:
    python visualize_dem.py
    python visualize_dem.py --input /path/to/dem.tif
"""

import os
import argparse
import logging

import numpy as np
import matplotlib.pyplot as plt
from osgeo import gdal

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_INPUT = os.path.join(PROJECT_ROOT, "data", "processed", "rasters", "dem.tif")
DEFAULT_OUTPUT = os.path.join(PROJECT_ROOT, "outputs", "figures", "dem_preview.png")

DOWNSAMPLE_FACTOR = 20  # Read 1 out of every N pixels to reduce memory usage


def visualize_dem(input_path: str, output_path: str, downsample: int = DOWNSAMPLE_FACTOR) -> None:
    """Render a downsampled DEM preview with terrain colormap."""
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"DEM not found: {input_path}")

    ds = gdal.Open(input_path)
    if ds is None:
        raise RuntimeError(f"GDAL could not open: {input_path}")

    band = ds.GetRasterBand(1)
    nodata = band.GetNoDataValue()
    cols, rows = ds.RasterXSize, ds.RasterYSize
    logger.info("DEM dimensions: %d x %d pixels", cols, rows)

    preview_w = cols // downsample
    preview_h = rows // downsample
    logger.info("Generating preview at %d x %d (1/%d scale) ...", preview_w, preview_h, downsample)

    data = band.ReadAsArray(buf_xsize=preview_w, buf_ysize=preview_h)
    if nodata is not None:
        data = np.ma.masked_equal(data, nodata)

    fig, ax = plt.subplots(figsize=(12, 10))
    img = ax.imshow(data, cmap="terrain")
    fig.colorbar(img, ax=ax, label="Elevation (m.a.s.l.)", shrink=0.8)
    ax.set_title(f"Digital Elevation Model — Peru (ESRI:102033, 30m)\n"
                 f"Preview at {100 / downsample:.0f}% resolution")
    ax.set_xlabel("X (projected)")
    ax.set_ylabel("Y (projected)")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    logger.info("Preview saved: %s", output_path)
    plt.close(fig)

    ds = None


def main():
    parser = argparse.ArgumentParser(description="Generate DEM preview image.")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Path to DEM raster.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output image path.")
    args = parser.parse_args()
    visualize_dem(args.input, args.output)


if __name__ == "__main__":
    main()
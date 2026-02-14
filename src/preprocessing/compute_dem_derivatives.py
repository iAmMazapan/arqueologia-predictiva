"""
Compute extended terrain derivatives from a Digital Elevation Model (DEM).

Generates ALL DEM-derived rasters for archaeological predictive modelling:

  v1 (baseline):
    - pendiente.tif         : Slope in degrees
    - rugosidad.tif         : Terrain Ruggedness Index (TRI)

  v2 (extended):
    - altitud.tif           : Elevation in metres (copy of DEM with LZW compression)
    - pisos_ecologicos.tif  : Reclassified elevation into Pulgar Vidal's natural regions
    - aspecto.tif           : Slope aspect in degrees (0-360, north=0)
    - curvatura.tif         : Profile curvature (second derivative of elevation)
    - tpi.tif               : Topographic Position Index (elevation vs. neighbourhood mean)
    - twi.tif               : Topographic Wetness Index — ln(a / tan(β))

All outputs preserve the input CRS (ESRI:102033), resolution (30 m), extent and
NoData convention. Existing outputs are skipped unless --force is passed.

Requires:
    - GDAL >= 3.4
    - NumPy
    - SciPy (ndimage)
    - tqdm

References:
    - Riley, S.J., DeGloria, S.D., Elliot, R. (1999). A terrain ruggedness
      index that quantifies topographic heterogeneity.
    - Pulgar Vidal, J. (1987). Geografía del Perú: Las Ocho Regiones Naturales.
    - Weiss, A. (2001). Topographic Position and Landforms Analysis (TPI).
    - Beven, K.J. & Kirkby, M.J. (1979). A physically based, variable
      contributing area model of basin hydrology (TWI).
    - Wilson, M.F.J., et al. (2007). Multiscale terrain analysis.

Note:
    This script supersedes compute_terrain_derivatives.py (v1), which only
    computed slope and TRI. All DEM derivatives are now unified here.

Usage:
    python compute_dem_derivatives.py
    python compute_dem_derivatives.py --input /path/to/dem.tif --output-dir /path/to/output/
    python compute_dem_derivatives.py --force   # Recompute even if outputs exist
"""

import os
import argparse
import logging
import sys

import numpy as np
from osgeo import gdal
from tqdm import tqdm

gdal.UseExceptions()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_INPUT = os.path.join(PROJECT_ROOT, "data", "processed", "rasters", "dem.tif")
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "processed", "rasters")

GTIFF_OPTIONS = ["COMPRESS=LZW", "TILED=YES", "PREDICTOR=2", "BIGTIFF=YES"]
NODATA = -9999.0

# ---------------------------------------------------------------------------
# Pisos ecológicos — Javier Pulgar Vidal (8 regiones naturales)
# ---------------------------------------------------------------------------
PISOS_ECOLOGICOS = [
    # (límite_inferior, límite_superior, código, nombre)
    (    0,   500,  1, "Chala (Costa)"),
    (  500,  2300,  2, "Yunga"),
    ( 2300,  3500,  3, "Quechua"),
    ( 3500,  4000,  4, "Suni (Jalca)"),
    ( 4000,  4800,  5, "Puna"),
    ( 4800,  6768,  6, "Janca (Cordillera)"),
    (    0,   400,  7, "Rupa-Rupa (Selva Alta)"),   # vertiente oriental
    (   80,   400,  8, "Omagua (Selva Baja)"),      # vertiente oriental
]

# Clasificación simplificada utilizable sin dato de vertiente:
# Solo altitud, sin distinguir vertiente oriental/occidental.
PISOS_SIMPLE = [
    # (min_alt, max_alt, código)
    (    0,   500,  1),   # Chala / Costa
    (  500,  2300,  2),   # Yunga
    ( 2300,  3500,  3),   # Quechua
    ( 3500,  4000,  4),   # Suni
    ( 4000,  4800,  5),   # Puna
    ( 4800, 99999,  6),   # Janca
]


# ===================================================================
# Helpers
# ===================================================================
def _write_raster(
    data: np.ndarray,
    reference_ds: gdal.Dataset,
    output_path: str,
    dtype=gdal.GDT_Float32,
    nodata: float = NODATA,
) -> None:
    """Write a NumPy array as a GeoTIFF using *reference_ds* for georeferencing."""
    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(
        output_path,
        reference_ds.RasterXSize,
        reference_ds.RasterYSize,
        1,
        dtype,
        options=GTIFF_OPTIONS,
    )
    out_ds.SetGeoTransform(reference_ds.GetGeoTransform())
    out_ds.SetProjection(reference_ds.GetProjection())
    band = out_ds.GetRasterBand(1)
    band.SetNoDataValue(nodata)
    band.WriteArray(data)
    band.FlushCache()
    out_ds = None
    logger.info("Saved → %s", output_path)


def _skip_or_compute(path: str, force: bool) -> bool:
    """Return True if the output already exists and force is False (skip)."""
    if os.path.isfile(path) and not force:
        logger.info("SKIP  (already exists): %s", os.path.basename(path))
        return True
    return False


def _gdal_progress(name: str):
    """Return a GDAL-compatible progress callback with tqdm bar."""
    pbar = tqdm(
        total=100, desc=f"  {name}", unit="%",
        bar_format="{l_bar}{bar}| {n:.0f}/{total:.0f}% [{elapsed}<{remaining}]",
    )
    prev = [0.0]

    def callback(complete, message, data):
        pct = int(complete * 100)
        delta = pct - prev[0]
        if delta > 0:
            pbar.update(delta)
            prev[0] = pct
        if complete >= 1.0:
            pbar.close()
        return 1

    return callback


# ===================================================================
# 1. PENDIENTE (slope)
# ===================================================================
def compute_pendiente(dem_ds: gdal.Dataset, output_path: str) -> None:
    """Compute slope in degrees from a DEM raster."""
    logger.info("Computing: pendiente (slope)")
    gdal.DEMProcessing(
        output_path,
        dem_ds,
        "slope",
        format="GTiff",
        slopeFormat="degree",
        creationOptions=GTIFF_OPTIONS,
        callback=_gdal_progress("pendiente"),
    )
    logger.info("Saved → %s", output_path)


# ===================================================================
# 2. RUGOSIDAD (TRI — Terrain Ruggedness Index)
# ===================================================================
def compute_rugosidad(dem_ds: gdal.Dataset, output_path: str) -> None:
    """Compute Terrain Ruggedness Index (TRI) from a DEM raster."""
    logger.info("Computing: rugosidad (TRI)")
    gdal.DEMProcessing(
        output_path,
        dem_ds,
        "TRI",
        format="GTiff",
        creationOptions=GTIFF_OPTIONS,
        callback=_gdal_progress("rugosidad"),
    )
    logger.info("Saved → %s", output_path)


# ===================================================================
# 3. ALTITUD
# ===================================================================
def compute_altitud(dem_ds: gdal.Dataset, output_path: str) -> None:
    """Copy DEM as altitud.tif with LZW compression."""
    logger.info("Computing: altitud")
    gdal.Translate(
        output_path,
        dem_ds,
        format="GTiff",
        creationOptions=GTIFF_OPTIONS,
    )
    logger.info("Saved → %s", output_path)


# ===================================================================
# 4. PISOS ECOLÓGICOS
# ===================================================================
def compute_pisos(dem_ds: gdal.Dataset, output_path: str) -> None:
    """Reclassify elevation into Pulgar Vidal's natural regions."""
    logger.info("Computing: pisos_ecologicos")
    band = dem_ds.GetRasterBand(1)
    rows = dem_ds.RasterYSize
    block_size = 1024

    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(
        output_path,
        dem_ds.RasterXSize,
        rows,
        1,
        gdal.GDT_Byte,
        options=GTIFF_OPTIONS,
    )
    out_ds.SetGeoTransform(dem_ds.GetGeoTransform())
    out_ds.SetProjection(dem_ds.GetProjection())
    out_band = out_ds.GetRasterBand(1)
    out_band.SetNoDataValue(0)

    n_blocks = (rows + block_size - 1) // block_size
    for y_off in tqdm(range(0, rows, block_size), total=n_blocks, desc="  pisos", unit="blk"):
        win_h = min(block_size, rows - y_off)
        elev = band.ReadAsArray(0, y_off, dem_ds.RasterXSize, win_h).astype(np.float32)
        result = np.zeros_like(elev, dtype=np.uint8)

        for lo, hi, code in PISOS_SIMPLE:
            mask = (elev >= lo) & (elev < hi) & (elev != NODATA)
            result[mask] = code

        result[elev == NODATA] = 0
        out_band.WriteArray(result, 0, y_off)

    out_band.FlushCache()
    out_ds = None
    logger.info("Saved → %s", output_path)


# ===================================================================
# 5. ASPECTO (orientación solar)
# ===================================================================
def compute_aspecto(dem_ds: gdal.Dataset, output_path: str) -> None:
    """Compute slope aspect (azimuth 0-360°) using GDAL DEMProcessing."""
    logger.info("Computing: aspecto")
    gdal.DEMProcessing(
        output_path,
        dem_ds,
        "aspect",
        format="GTiff",
        creationOptions=GTIFF_OPTIONS,
        zeroForFlat=True,
        callback=_gdal_progress("aspecto"),
    )
    logger.info("Saved → %s", output_path)


# ===================================================================
# 6. CURVATURA (profile curvature)
# ===================================================================
def compute_curvatura(dem_ds: gdal.Dataset, output_path: str) -> None:
    """Compute profile curvature as the Laplacian of the DEM (second derivative)."""
    logger.info("Computing: curvatura")
    from scipy.ndimage import convolve

    band = dem_ds.GetRasterBand(1)
    rows = dem_ds.RasterYSize
    cols = dem_ds.RasterXSize
    gt = dem_ds.GetGeoTransform()
    cell_size = abs(gt[1])  # 30 m

    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(
        output_path, cols, rows, 1, gdal.GDT_Float32, options=GTIFF_OPTIONS
    )
    out_ds.SetGeoTransform(gt)
    out_ds.SetProjection(dem_ds.GetProjection())
    out_band = out_ds.GetRasterBand(1)
    out_band.SetNoDataValue(NODATA)

    kernel = np.array([[0, 1, 0],
                       [1, -4, 1],
                       [0, 1, 0]], dtype=np.float64) / (cell_size ** 2)

    block = 1024
    n_blocks = (rows + block - 1) // block
    for y_off in tqdm(range(0, rows, block), total=n_blocks, desc="  curvatura", unit="blk"):
        y_start = max(y_off - 1, 0)
        y_end = min(y_off + block + 1, rows)
        elev = band.ReadAsArray(0, y_start, cols, y_end - y_start).astype(np.float64)

        nodata_mask = (elev == NODATA)
        elev[nodata_mask] = np.nan

        curv = convolve(elev, kernel, mode="nearest")

        trim_top = y_off - y_start
        trim_bot = y_end - min(y_off + block, rows)
        if trim_bot > 0:
            curv = curv[trim_top:-trim_bot]
        else:
            curv = curv[trim_top:]

        nodata_out = np.isnan(curv)
        curv[nodata_out] = NODATA
        out_band.WriteArray(curv.astype(np.float32), 0, y_off)

    out_band.FlushCache()
    out_ds = None
    logger.info("Saved → %s", output_path)


# ===================================================================
# 7. TPI — Topographic Position Index
# ===================================================================
def compute_tpi(dem_ds: gdal.Dataset, output_path: str, radius: int = 10) -> None:
    """
    Compute TPI = elevation - mean(elevation in annular neighbourhood).

    Parameters
    ----------
    radius : int
        Radius in pixels for the neighbourhood ring (default 10 → 300 m).
    """
    logger.info("Computing: TPI (radius=%d px = %d m)", radius, radius * 30)
    from scipy.ndimage import convolve

    band = dem_ds.GetRasterBand(1)
    rows = dem_ds.RasterYSize
    cols = dem_ds.RasterXSize

    # Build annular kernel
    y, x = np.ogrid[-radius:radius + 1, -radius:radius + 1]
    dist = np.sqrt(x ** 2 + y ** 2)
    kernel = ((dist <= radius) & (dist > 0)).astype(np.float64)
    kernel /= kernel.sum()

    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(
        output_path, cols, rows, 1, gdal.GDT_Float32, options=GTIFF_OPTIONS
    )
    out_ds.SetGeoTransform(dem_ds.GetGeoTransform())
    out_ds.SetProjection(dem_ds.GetProjection())
    out_band = out_ds.GetRasterBand(1)
    out_band.SetNoDataValue(NODATA)

    block = 1024
    pad = radius
    n_blocks = (rows + block - 1) // block
    for y_off in tqdm(range(0, rows, block), total=n_blocks, desc="  TPI", unit="blk"):
        y_start = max(y_off - pad, 0)
        y_end = min(y_off + block + pad, rows)
        elev = band.ReadAsArray(0, y_start, cols, y_end - y_start).astype(np.float64)

        nodata_mask = (elev == NODATA)
        elev[nodata_mask] = np.nan

        mean_elev = convolve(elev, kernel, mode="nearest")
        tpi = elev - mean_elev

        trim_top = y_off - y_start
        trim_bot = y_end - min(y_off + block, rows)
        if trim_bot > 0:
            tpi = tpi[trim_top:-trim_bot]
            nodata_mask = nodata_mask[trim_top:-trim_bot]
        else:
            tpi = tpi[trim_top:]
            nodata_mask = nodata_mask[trim_top:]

        tpi[nodata_mask] = NODATA
        tpi_clean = np.where(np.isnan(tpi), NODATA, tpi)
        out_band.WriteArray(tpi_clean.astype(np.float32), 0, y_off)

    out_band.FlushCache()
    out_ds = None
    logger.info("Saved → %s", output_path)


# ===================================================================
# 8. TWI — Topographic Wetness Index
# ===================================================================
def compute_twi(dem_ds: gdal.Dataset, slope_path: str, output_path: str) -> None:
    """
    Compute TWI = ln(a / tan(β)), where:
        a = upslope contributing area
        β = slope in radians

    Simplified approach: uses slope from existing raster and a uniform
    contributing area proxy (SCA = cell_size).
    For production use, a full D-inf flow routing (e.g. via WhiteboxTools)
    would be preferable.
    """
    logger.info("Computing: TWI (simplified)")
    band = dem_ds.GetRasterBand(1)
    rows = dem_ds.RasterYSize
    cols = dem_ds.RasterXSize
    gt = dem_ds.GetGeoTransform()
    cell_size = abs(gt[1])

    slope_ds = gdal.Open(slope_path)
    if slope_ds is None:
        raise FileNotFoundError(
            f"Slope raster not found: {slope_path}. "
            "Run this script first without --force to generate pendiente.tif."
        )

    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(
        output_path, cols, rows, 1, gdal.GDT_Float32, options=GTIFF_OPTIONS
    )
    out_ds.SetGeoTransform(gt)
    out_ds.SetProjection(dem_ds.GetProjection())
    out_band = out_ds.GetRasterBand(1)
    out_band.SetNoDataValue(NODATA)

    slope_band = slope_ds.GetRasterBand(1)

    block = 1024
    n_blocks = (rows + block - 1) // block
    for y_off in tqdm(range(0, rows, block), total=n_blocks, desc="  TWI", unit="blk"):
        win_h = min(block, rows - y_off)
        elev = band.ReadAsArray(0, y_off, cols, win_h).astype(np.float64)
        slope_deg = slope_band.ReadAsArray(0, y_off, cols, win_h).astype(np.float64)

        nodata_mask = (elev == NODATA)

        slope_rad = np.deg2rad(slope_deg)
        slope_rad = np.clip(slope_rad, np.deg2rad(0.1), None)

        sca = cell_size
        twi = np.log(sca / np.tan(slope_rad))

        twi[nodata_mask] = NODATA
        twi_clean = np.where(np.isnan(twi) | np.isinf(twi), NODATA, twi)
        out_band.WriteArray(twi_clean.astype(np.float32), 0, y_off)

    out_band.FlushCache()
    slope_ds = None
    out_ds = None
    logger.info("Saved → %s", output_path)


# ===================================================================
# CLI entry point
# ===================================================================
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute DEM-derived terrain variables for archaeological modelling (v2).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", default=DEFAULT_INPUT,
        help="Path to input DEM raster (default: data/processed/rasters/dem.tif).",
    )
    parser.add_argument(
        "--output-dir", default=DEFAULT_OUTPUT_DIR,
        help="Output directory for generated rasters.",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Recompute outputs even if they already exist.",
    )
    parser.add_argument(
        "--tpi-radius", type=int, default=10,
        help="TPI neighbourhood radius in pixels (default: 10 = 300 m).",
    )
    args = parser.parse_args()

    # Validate input
    dem_ds = gdal.Open(args.input)
    if dem_ds is None:
        logger.error("Cannot open DEM: %s", args.input)
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)
    logger.info("DEM: %s (%d × %d)", args.input, dem_ds.RasterXSize, dem_ds.RasterYSize)
    logger.info("Output dir: %s", args.output_dir)

    # Define outputs
    outputs = {
        "pendiente":        os.path.join(args.output_dir, "pendiente.tif"),
        "rugosidad":        os.path.join(args.output_dir, "rugosidad.tif"),
        "altitud":          os.path.join(args.output_dir, "altitud.tif"),
        "pisos_ecologicos": os.path.join(args.output_dir, "pisos_ecologicos.tif"),
        "aspecto":          os.path.join(args.output_dir, "aspecto.tif"),
        "curvatura":        os.path.join(args.output_dir, "curvatura.tif"),
        "tpi":              os.path.join(args.output_dir, "tpi.tif"),
        "twi":              os.path.join(args.output_dir, "twi.tif"),
    }

    computed, skipped = 0, 0

    # --- 1. Pendiente ---
    if _skip_or_compute(outputs["pendiente"], args.force):
        skipped += 1
    else:
        compute_pendiente(dem_ds, outputs["pendiente"])
        computed += 1

    # --- 2. Rugosidad (TRI) ---
    if _skip_or_compute(outputs["rugosidad"], args.force):
        skipped += 1
    else:
        compute_rugosidad(dem_ds, outputs["rugosidad"])
        computed += 1

    # --- 3. Altitud ---
    if _skip_or_compute(outputs["altitud"], args.force):
        skipped += 1
    else:
        compute_altitud(dem_ds, outputs["altitud"])
        computed += 1

    # --- 4. Pisos ecológicos ---
    if _skip_or_compute(outputs["pisos_ecologicos"], args.force):
        skipped += 1
    else:
        compute_pisos(dem_ds, outputs["pisos_ecologicos"])
        computed += 1

    # --- 5. Aspecto ---
    if _skip_or_compute(outputs["aspecto"], args.force):
        skipped += 1
    else:
        compute_aspecto(dem_ds, outputs["aspecto"])
        computed += 1

    # --- 6. Curvatura ---
    if _skip_or_compute(outputs["curvatura"], args.force):
        skipped += 1
    else:
        compute_curvatura(dem_ds, outputs["curvatura"])
        computed += 1

    # --- 7. TPI ---
    if _skip_or_compute(outputs["tpi"], args.force):
        skipped += 1
    else:
        compute_tpi(dem_ds, outputs["tpi"], radius=args.tpi_radius)
        computed += 1

    # --- 8. TWI ---
    if _skip_or_compute(outputs["twi"], args.force):
        skipped += 1
    else:
        slope_path = os.path.join(args.output_dir, "pendiente.tif")
        compute_twi(dem_ds, slope_path, outputs["twi"])
        computed += 1

    dem_ds = None

    logger.info("=" * 60)
    logger.info("Done. Computed: %d | Skipped: %d | Total: %d", computed, skipped, computed + skipped)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

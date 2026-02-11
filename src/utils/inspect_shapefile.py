"""Inspect a vector file (shapefile, GeoPackage, GeoJSON).

Prints column names, sample rows, geometry type, CRS, and extent.
Useful for diagnosing attribute names and geometry issues before
processing.

Usage:
    python inspect_shapefile.py /path/to/file.shp
    python inspect_shapefile.py /path/to/layer.gpkg
"""

import argparse
import logging

import geopandas as gpd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def inspect(filepath: str, n_rows: int = 5) -> None:
    """Read a vector file and print diagnostic information."""
    logger.info("Reading: %s", filepath)
    gdf = gpd.read_file(filepath)

    print(f"\n{'=' * 60}")
    print(f"FILE: {filepath}")
    print(f"{'=' * 60}")
    print(f"Rows:          {len(gdf)}")
    print(f"Columns:       {gdf.columns.tolist()}")
    print(f"CRS:           {gdf.crs}")
    print(f"Geometry type: {gdf.geom_type.unique().tolist()}")
    print(f"Has Z coords:  {gdf.has_z.any()}")
    print(f"Bounds:        {gdf.total_bounds}")
    print(f"\n--- Sample ({n_rows} rows) ---")
    print(gdf.head(n_rows))
    print(f"\n--- Dtypes ---")
    print(gdf.dtypes)


def main():
    parser = argparse.ArgumentParser(description="Inspect a vector geospatial file.")
    parser.add_argument("filepath", help="Path to the vector file (.shp, .gpkg, .geojson).")
    parser.add_argument("--rows", type=int, default=5, help="Number of sample rows to display.")
    args = parser.parse_args()
    inspect(args.filepath, args.rows)


if __name__ == "__main__":
    main()
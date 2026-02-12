"""Download ASTER GDEM v3 tiles for Peru.

Scrapes tile URLs from the GeoGPSPeru catalog (JavaScript-based index),
converts Google Drive view links to direct download links, and saves
each tile as a .zip archive.

Data source:
    GeoGPSPeru ASTER GDEM v3 catalog
    https://geogpsperu.github.io/dem.github.com/data/DEMASTER_3.js

Usage:
    python download_dem.py
    python download_dem.py --output-dir /path/to/tiles/
"""

import os
import re
import json
import time
import argparse
import logging

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "raw", "dem_tiles")
CATALOG_URL = "https://geogpsperu.github.io/dem.github.com/data/DEMASTER_3.js"


def parse_js_catalog(js_text: str) -> dict | None:
    """Parse JavaScript variable assignment into a Python dict.

    The source file has the form: var json_DEMASTER_3 = { ... };
    This function strips the variable declaration and trailing semicolon.
    """
    try:
        start = js_text.find("{")
        if start == -1:
            return None
        json_str = js_text[start:].strip().rstrip(";")
        return json.loads(json_str)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("JSON parsing failed (%s). Falling back to regex.", exc)
        return None


def extract_links_regex(text: str) -> list[dict]:
    """Fallback: extract tile codes and download URLs via regex."""
    pattern = r'"codigo":\s*"([^"]+)",\s*"descarga":\s*"(https:[^"]+)"'
    matches = re.findall(pattern, text)
    return [{"properties": {"codigo": code, "descarga": url}} for code, url in matches]


def gdrive_direct_url(url: str) -> str:
    """Convert a Google Drive view URL to a direct download URL."""
    url = url.replace("\\/", "/")
    file_id = None
    if "id=" in url:
        file_id = url.split("id=")[1].split("&")[0]
    elif "/file/d/" in url:
        file_id = url.split("/file/d/")[1].split("/")[0]
    if file_id:
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url


def download_tiles(output_dir: str) -> None:
    """Download all ASTER GDEM tiles to the specified directory."""
    os.makedirs(output_dir, exist_ok=True)

    logger.info("Fetching catalog from %s", CATALOG_URL)
    response = requests.get(CATALOG_URL, timeout=30)
    response.raise_for_status()

    catalog = parse_js_catalog(response.text)
    if catalog and "features" in catalog:
        tiles = catalog["features"]
        logger.info("Catalog parsed via JSON: %d tiles found.", len(tiles))
    else:
        tiles = extract_links_regex(response.text)
        logger.info("Catalog parsed via regex: %d tiles found.", len(tiles))

    for i, item in enumerate(tiles, 1):
        props = item.get("properties", item)
        code = props.get("codigo", f"UNKNOWN_{i}")
        raw_url = props.get("descarga", "")
        if not raw_url:
            continue

        output_path = os.path.join(output_dir, f"{code}.zip")
        if os.path.exists(output_path):
            logger.info("[%d/%d] %s -- already exists, skipping.", i, len(tiles), code)
            continue

        download_url = gdrive_direct_url(raw_url)
        logger.info("[%d/%d] Downloading %s ...", i, len(tiles), code)

        try:
            r = requests.get(download_url, stream=True, timeout=60)
            if r.status_code == 200:
                with open(output_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info("[%d/%d] %s -- saved.", i, len(tiles), code)
            else:
                logger.warning("[%d/%d] %s -- HTTP %d", i, len(tiles), code, r.status_code)
        except requests.RequestException as exc:
            logger.error("[%d/%d] %s -- failed: %s", i, len(tiles), code, exc)

        time.sleep(0.5)

    logger.info("Download complete. Tiles saved to %s", output_dir)


def main():
    parser = argparse.ArgumentParser(description="Download ASTER GDEM v3 tiles for Peru.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory.")
    args = parser.parse_args()
    download_tiles(args.output_dir)


if __name__ == "__main__":
    main()
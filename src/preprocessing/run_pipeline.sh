#!/bin/bash
# ============================================================================
# run_pipeline.sh — Extract DEM zip archives and merge into unified raster.
#
# Steps:
#   1. Extract *_dem.tif files from data/raw/dem_tiles/*.zip using 7z or unzip
#   2. Call merge_tiles.py to build mosaic and reproject to ESRI:102033
#
# Usage:
#   bash src/preprocessing/run_pipeline.sh
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

TILES_DIR="${PROJECT_ROOT}/data/raw/dem_tiles"
MERGE_SCRIPT="${SCRIPT_DIR}/merge_tiles.py"

echo "================================================================"
echo "  DEM Processing Pipeline"
echo "  Tiles dir: ${TILES_DIR}"
echo "================================================================"

# --- Step 1: Extract zip archives -------------------------------------------

cd "${TILES_DIR}" || { echo "ERROR: directory not found: ${TILES_DIR}"; exit 1; }

total_files=$(find . -maxdepth 1 -name "*.zip" 2>/dev/null | wc -l)
current=0

if [[ "${total_files}" -eq 0 ]]; then
    echo "No .zip files found in ${TILES_DIR}. Skipping extraction."
else
    # Select extraction tool
    if command -v 7z &> /dev/null; then
        EXTRACT_CMD="7z"
    elif command -v unzip &> /dev/null; then
        EXTRACT_CMD="unzip"
    else
        echo "ERROR: Install p7zip-full or unzip."; exit 1
    fi

    echo "[Step 1] Extracting ${total_files} archives ..."

    for f in *.zip; do
        current=$((current + 1))
        percent=$((current * 100 / total_files))
        printf "\r  Progress: [%3d%%] %3d / %3d — %s" \
            "${percent}" "${current}" "${total_files}" "${f}"

        if [[ "${EXTRACT_CMD}" == "7z" ]]; then
            7z x "${f}" -y -aos -bso0 > /dev/null 2>&1 || true
        else
            unzip -oq "${f}" 2>/dev/null || true
        fi
    done
    echo ""
    echo "[Step 1] Extraction complete."
fi

# --- Step 2: Merge and reproject --------------------------------------------

echo "[Step 2] Merging tiles and reprojecting ..."

if [[ -f "${MERGE_SCRIPT}" ]]; then
    python3 "${MERGE_SCRIPT}"
else
    echo "ERROR: merge script not found: ${MERGE_SCRIPT}"
    exit 1
fi

echo "================================================================"
echo "  Pipeline finished. Check data/processed/rasters/dem.tif"
echo "================================================================"

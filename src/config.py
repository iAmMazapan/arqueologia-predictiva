"""
src/config.py — Single Source of Truth for the Predictive Archaeological Model.

Every notebook imports its raster registry, paths, and visualization parameters
from here.  To add a new variable to the **entire** pipeline you only need to
append one entry to RASTER_REGISTRY below.

Usage in notebooks
------------------
    import sys, os
    sys.path.insert(0, os.path.abspath(".."))
    from src.config import (
        RASTER_REGISTRY, RASTER_DIR, FIGURES_BASE,
        get_rasters, get_raster_paths, CRS, PIXEL_SIZE,
    )
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# 1. PROJECT-LEVEL CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

CRS          = "ESRI:102033"       # South America Albers Equal Area Conic
PIXEL_SIZE   = 30                  # metres
DEM_SOURCE   = "ASTER GDEM v3"

# ─────────────────────────────────────────────────────────────────────────────
# 2. DIRECTORY STRUCTURE
# ─────────────────────────────────────────────────────────────────────────────
RASTER_DIR   = os.path.join(PROJECT_ROOT, "data", "processed", "rasters")
SAMPLES_DIR  = os.path.join(PROJECT_ROOT, "data", "processed", "samples")
FEATURES_DIR = os.path.join(PROJECT_ROOT, "data", "features")
MODELS_DIR   = os.path.join(PROJECT_ROOT, "models")
RAW_DIR      = os.path.join(PROJECT_ROOT, "data", "raw", "sitiosarqueologicos")
FIGURES_BASE = os.path.join(PROJECT_ROOT, "outputs", "figures")

# Per-notebook figure directories
FIGURES_DIRS = {
    "01_validation":      os.path.join(FIGURES_BASE, "01_validation"),
    "02_sampling":        os.path.join(FIGURES_BASE, "02_sampling"),
    "03_feature_eng":     os.path.join(FIGURES_BASE, "03_feature_engineering"),
    "04_training":        os.path.join(FIGURES_BASE, "04_training"),
    "05_prediction":      os.path.join(FIGURES_BASE, "05_prediction"),
    "06_multiregion":     os.path.join(FIGURES_BASE, "06_multiregion"),
}

# Reference raster (used for alignment checks)
REF_RASTER   = os.path.join(RASTER_DIR, "dem.tif")


# ─────────────────────────────────────────────────────────────────────────────
# 3. RASTER VARIABLE REGISTRY
# ─────────────────────────────────────────────────────────────────────────────
class VarType(Enum):
    """Variable type — drives visualisation and preprocessing decisions."""
    CONTINUOUS  = "continuous"
    CATEGORICAL = "categorical"
    DISTANCE    = "distance"


class VarGroup(Enum):
    """Logical grouping for visualisation panels."""
    TERRAIN    = "terrain"
    ECOLOGICAL = "ecological"
    HYDROLOGY  = "hydrology"
    ROAD       = "road"
    CONTEXT    = "context"


@dataclass(frozen=True)
class RasterVar:
    """Metadata for a single predictor raster layer.

    Attributes
    ----------
    name        : column name in the training dataset (must be unique).
    filename    : raster filename inside RASTER_DIR.
    var_type    : continuous / categorical / distance.
    group       : logical group for visualization.
    label       : human-readable label for figures.
    unit        : unit string for colorbars.
    cmap        : matplotlib colormap name.
    vmin / vmax : fixed colour-scale limits (None → auto from percentile).
    symmetric   : if True, colour scale is centred on 0.
    version     : "v1" (baseline) or "v2" (DEM derivatives).
    description : archaeological hypothesis / rationale.
    cat_labels  : {code: label} for categorical variables.
    cat_colors  : {code: hex_color} for categorical variables.
    """
    name:        str
    filename:    str
    var_type:    VarType
    group:       VarGroup
    label:       str
    unit:        str           = ""
    cmap:        str           = "viridis"
    vmin:        Optional[float] = None
    vmax:        Optional[float] = None
    symmetric:   bool          = False
    version:     str           = "v1"
    description: str           = ""
    cat_labels:  Optional[Dict[int, str]] = None
    cat_colors:  Optional[Dict[int, str]] = None

    @property
    def path(self) -> str:
        """Absolute path to the raster file."""
        return os.path.join(RASTER_DIR, self.filename)

    @property
    def exists(self) -> bool:
        return os.path.exists(self.path)


# ── Registry ──────────────────────────────────────────────────────────────────
# To add a new variable: append ONE RasterVar here.  The entire pipeline
# (validation → feature engineering → training → prediction) picks it up
# automatically.

RASTER_REGISTRY: List[RasterVar] = [

    # ── v1: Terrain ──────────────────────────────────────────────────────────
    RasterVar(
        name="pendiente", filename="pendiente.tif",
        var_type=VarType.CONTINUOUS, group=VarGroup.TERRAIN,
        label="Slope", unit="°", cmap="magma",
        version="v1",
        description="Terrain inclination. Flat areas preferred for habitation.",
    ),
    RasterVar(
        name="rugosidad", filename="rugosidad.tif",
        var_type=VarType.CONTINUOUS, group=VarGroup.TERRAIN,
        label="Terrain Ruggedness (TRI)", unit="Index", cmap="magma",
        version="v1",
        description="Terrain irregularity. Smoother terrain facilitates construction.",
    ),

    # ── v1: Distance (hydrology) ─────────────────────────────────────────────
    RasterVar(
        name="dist_rios", filename="distancia_rios.tif",
        var_type=VarType.DISTANCE, group=VarGroup.HYDROLOGY,
        label="Dist. Rivers", unit="m", cmap="viridis",
        version="v1",
        description="Euclidean distance to watercourses. Water access is fundamental.",
    ),
    RasterVar(
        name="dist_lagos", filename="distancia_lagos.tif",
        var_type=VarType.DISTANCE, group=VarGroup.HYDROLOGY,
        label="Dist. Lakes", unit="m", cmap="viridis",
        version="v1",
        description="Distance to lacustrine bodies. Aquatic resources and ritual sites.",
    ),

    # ── v1: Distance (road network) ──────────────────────────────────────────
    RasterVar(
        name="dist_qhapaq", filename="distancia_qhapaq_nan.tif",
        var_type=VarType.DISTANCE, group=VarGroup.ROAD,
        label="Dist. Qhapaq Ñan", unit="m", cmap="viridis",
        version="v1",
        description="Distance to Inca road network. Connectivity → administrative sites.",
    ),

    # ── v1: Distance (archaeological context) ────────────────────────────────
    RasterVar(
        name="dist_declarados", filename="distancia_declarados.tif",
        var_type=VarType.DISTANCE, group=VarGroup.CONTEXT,
        label="Dist. Declared Sites", unit="m", cmap="viridis",
        version="v1",
        description="Proximity to registered point sites. Clustering effect.",
    ),
    RasterVar(
        name="dist_g1", filename="distancia_g1.tif",
        var_type=VarType.DISTANCE, group=VarGroup.CONTEXT,
        label="Dist. Monumental Nuclei (G1)", unit="m", cmap="viridis",
        version="v1",
        description="Proximity to major urban/ceremonial centres.",
    ),
    RasterVar(
        name="dist_g2", filename="distancia_g2.tif",
        var_type=VarType.DISTANCE, group=VarGroup.CONTEXT,
        label="Dist. Cultural Landscapes (G2)", unit="m", cmap="viridis",
        version="v1",
        description="Proximity to terraces, canals, extensive modification areas.",
    ),
    RasterVar(
        name="dist_g3", filename="distancia_g3.tif",
        var_type=VarType.DISTANCE, group=VarGroup.CONTEXT,
        label="Dist. Isolated Evidence (G3)", unit="m", cmap="viridis",
        version="v1",
        description="Spatial continuity of isolated archaeological findings.",
    ),

    # ── v2: DEM Derivatives (terrain) ────────────────────────────────────────
    RasterVar(
        name="altitud", filename="altitud.tif",
        var_type=VarType.CONTINUOUS, group=VarGroup.TERRAIN,
        label="Elevation", unit="m", cmap="terrain",
        version="v2",
        description="Altitude determines ecological zones and habitability.",
    ),
    RasterVar(
        name="aspecto", filename="aspecto.tif",
        var_type=VarType.CONTINUOUS, group=VarGroup.TERRAIN,
        label="Slope Aspect", unit="°", cmap="twilight_shifted",
        vmin=0, vmax=360,
        version="v2",
        description="Slope orientation. North-facing slopes receive more sunlight.",
    ),
    RasterVar(
        name="curvatura", filename="curvatura.tif",
        var_type=VarType.CONTINUOUS, group=VarGroup.TERRAIN,
        label="Profile Curvature", unit="1/m", cmap="RdBu_r",
        symmetric=True,
        version="v2",
        description="Surface concavity/convexity affects water flow and erosion.",
    ),
    RasterVar(
        name="tpi", filename="tpi.tif",
        var_type=VarType.CONTINUOUS, group=VarGroup.TERRAIN,
        label="Topographic Position Index", unit="m", cmap="RdBu_r",
        symmetric=True,
        version="v2",
        description="Relative elevation: ridges (+) vs valleys (−).",
    ),
    RasterVar(
        name="twi", filename="twi.tif",
        var_type=VarType.CONTINUOUS, group=VarGroup.TERRAIN,
        label="Topographic Wetness Index", unit="ln(a/tan β)", cmap="YlGnBu",
        version="v2",
        description="Soil moisture proxy. High TWI → flat, low-gradient areas.",
    ),

    # ── v2: DEM Derivatives (ecological) ─────────────────────────────────────
    RasterVar(
        name="pisos_ecologicos", filename="pisos_ecologicos.tif",
        var_type=VarType.CATEGORICAL, group=VarGroup.ECOLOGICAL,
        label="Ecological Zones (Pulgar Vidal)", unit="",
        version="v2",
        description="Altitudinal classification. Each zone has distinct resources.",
        cat_labels={
            1: "Chala (Costa)",
            2: "Yunga",
            3: "Quechua",
            4: "Suni (Jalca)",
            5: "Puna",
            6: "Janca (Cordillera)",
        },
        cat_colors={
            1: "#f2e85c",
            2: "#f0a830",
            3: "#6abf4b",
            4: "#2d8e4e",
            5: "#8c6d46",
            6: "#d9d9d9",
        },
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# 4. CONVENIENCE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_registry() -> List[RasterVar]:
    """Return the full raster registry."""
    return RASTER_REGISTRY


def get_rasters(
    *,
    version: Optional[str] = None,
    var_type: Optional[VarType] = None,
    group: Optional[VarGroup] = None,
) -> List[RasterVar]:
    """Filter the registry by version, type, and/or group."""
    out = RASTER_REGISTRY
    if version is not None:
        out = [r for r in out if r.version == version]
    if var_type is not None:
        out = [r for r in out if r.var_type == var_type]
    if group is not None:
        out = [r for r in out if r.group == group]
    return out


def get_raster_paths(
    *,
    version: Optional[str] = None,
    var_type: Optional[VarType] = None,
) -> Dict[str, str]:
    """Return {name: absolute_path} dict, optionally filtered."""
    return {r.name: r.path for r in get_rasters(version=version, var_type=var_type)}


def get_feature_names(
    *,
    version: Optional[str] = None,
) -> List[str]:
    """Ordered list of feature column names (matches training dataset columns)."""
    return [r.name for r in get_rasters(version=version)]


def figures_dir(notebook_key: str) -> str:
    """Return and create the figure directory for a notebook key.

    Parameters
    ----------
    notebook_key : one of '01_validation', '02_sampling', etc.
    """
    d = FIGURES_DIRS[notebook_key]
    os.makedirs(d, exist_ok=True)
    return d


# ─────────────────────────────────────────────────────────────────────────────
# 5. QUICK SANITY CHECK (when run as a script)
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Project root  : {PROJECT_ROOT}")
    print(f"Raster dir    : {RASTER_DIR}")
    print(f"CRS           : {CRS}")
    print(f"Pixel size    : {PIXEL_SIZE} m")
    print(f"Total vars    : {len(RASTER_REGISTRY)}")
    print(f"  v1          : {len(get_rasters(version='v1'))}")
    print(f"  v2          : {len(get_rasters(version='v2'))}")
    print()

    for r in RASTER_REGISTRY:
        status = "OK" if r.exists else "MISSING"
        print(f"  [{status:^7}]  {r.version}  {r.name:<20}  {r.filename}")

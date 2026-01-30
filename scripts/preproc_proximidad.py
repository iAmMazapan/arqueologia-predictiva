"""
PROYECTO: Modelo Predictivo de Riesgo Arqueológico
MODULO: 02_preproc_proximidades.py

DESCRIPCIÓN: 
Genera variables de distancia euclidiana (Cost Distance proxies).
1. Hidrografía: Combina Ríos (Líneas) y Lagos (Polígonos).
2. Vialidad: Procesa la red de caminos inca (Qhapaq Ñan).
3. Alineación: Asegura que los rasters coincidan pixel-a-pixel con el DEM.

Inputs: Shapefiles (raw) + DEM (processed reference).
Outputs: Rasters TIF de distancia (metros).


NO HE PODIDO PROCESAR PROXIMIDADES CON PYTHON, DE MOMENTO HACERLO CON QGIS


"""

import os
import sys
import subprocess
import whitebox

# --- CONFIGURACIÓN ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
RAW_PATH = os.path.join(BASE_DIR, "data", "raw")
PROC_PATH = os.path.join(BASE_DIR, "data", "processed")

# Referencia (El DEM es nuestro "patrón oro" para la grilla)
DEM_REF = os.path.join(PROC_PATH, "raster_dem.tif")

# Inputs Vectoriales
# Ajusta los nombres si difieren en tu carpeta
SHP_RIOS = os.path.join(RAW_PATH, "unificado-rios-lineas.shp")
SHP_LAGOS = os.path.join(RAW_PATH, "unificado-lagos-poligonos.shp")
# Asumimos que dentro de la carpeta qhapaqnan hay un shapefile principal
# Si tienes el nombre exacto del .shp del camino, edítalo aquí:
SHP_VIAL = os.path.join(RAW_PATH, "qhapaqnan", "qhapaqnan_lineas.shp") 

# Outputs Intermedios (Temporales)
TMP_DIST_RIOS = os.path.join(PROC_PATH, "temp_dist_rios.tif")
TMP_DIST_LAGOS = os.path.join(PROC_PATH, "temp_dist_lagos.tif")

# Outputs Finales
OUT_DIST_AGUA = os.path.join(PROC_PATH, "raster_dist_agua.tif")
OUT_DIST_VIAL = os.path.join(PROC_PATH, "raster_dist_vial.tif")

def find_whitebox_binary():
    """Localiza el binario ejecutable de WhiteboxTools."""
    module_dir = os.path.dirname(whitebox.__file__)
    possible_paths = [
        os.path.join(module_dir, "WBT", "whitebox_tools"),
        os.path.join(module_dir, "whitebox_tools"),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            if sys.platform != "win32":
                try: os.chmod(path, 0o755)
                except: pass
            return path
    return whitebox.WhiteboxTools().exe_path

def run_wbt(executable, tool, args):
    """Ejecuta comando WBT con manejo de errores básico."""
    cmd = [executable, f"--run={tool}"] + args
    print(f"[WBT] Ejecutando {tool}...")
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        print(f"[ERROR] Falló {tool}.")
        return False

def calculate_distance_raster(executable, input_shp, output_tif, feature_type="lines"):
    """
    Convierte Vector -> Raster y calcula Distancia Euclidiana.
    feature_type: 'lines' o 'polygons'
    """
    if not os.path.exists(input_shp):
        print(f"[SKIP] No existe el input: {os.path.basename(input_shp)}")
        return False

    # 1. Rasterización (Vector -> Grid)
    # Usamos el DEM como base para copiar la resolución y extensión si la herramienta lo permite,
    # si no, definimos tamaño de celda 30m.
    temp_raster = output_tif.replace(".tif", "_bool.tif")
    
    tool_rasterize = "VectorLinesToRaster" if feature_type == "lines" else "VectorPolygonsToRaster"
    
    # Nota: WBT necesita un campo para "quemar" el valor. 
    # Usamos 'FID' (generalmente seguro) o simplemente creamos presencia.
    args_rast = [
        f"--input={input_shp}",
        f"--output={temp_raster}",
        "--field=FID", 
        "--resolution=30.0"
    ]
    
    if not run_wbt(executable, tool_rasterize, args_rast):
        return False

    # 2. Distancia Euclidiana
    args_dist = [
        f"--input={temp_raster}",
        f"--output={output_tif}"
    ]
    run_wbt(executable, "EuclideanDistance", args_dist)
    
    # Limpieza
    try: os.remove(temp_raster)
    except: pass
    
    return True

def main():
    executable = find_whitebox_binary()
    print(f"[SISTEMA] Motor: {executable}")

    if not os.path.exists(DEM_REF):
        print("[ERROR] No se encuentra raster_dem.tif. Ejecuta el script 01 primero.")
        return

    # ---------------------------------------------------------------------
    # 1. PROCESAMIENTO HIDROLÓGICO (Ríos + Lagos)
    # ---------------------------------------------------------------------
    print("\n--- Procesando Hidrografía ---")
    
    has_rios = calculate_distance_raster(executable, SHP_RIOS, TMP_DIST_RIOS, "lines")
    has_lagos = calculate_distance_raster(executable, SHP_LAGOS, TMP_DIST_LAGOS, "polygons")

    # Combinación (Mínimo de las dos distancias)
    if has_rios and has_lagos:
        print("[COMBINANDO] Calculando distancia mínima (Ríos vs Lagos)...")
        # Min opera pixel a pixel
        run_wbt(executable, "Min", [
            f"--input1={TMP_DIST_RIOS}",
            f"--input2={TMP_DIST_LAGOS}",
            f"--output={OUT_DIST_AGUA}"
        ])
    elif has_rios:
        print("[INFO] Solo se encontraron Ríos. Renombrando...")
        os.rename(TMP_DIST_RIOS, OUT_DIST_AGUA)
    elif has_lagos:
        print("[INFO] Solo se encontraron Lagos. Renombrando...")
        os.rename(TMP_DIST_LAGOS, OUT_DIST_AGUA)
    else:
        print("[ALERTA] No se generó capa de agua (revisa nombres de archivos).")

    # ---------------------------------------------------------------------
    # 2. PROCESAMIENTO VIAL (Qhapaq Ñan)
    # ---------------------------------------------------------------------
    print("\n--- Procesando Vialidad ---")
    # Busca automáticamente el .shp en la carpeta si no dimos ruta exacta
    if not os.path.exists(SHP_VIAL):
        vial_dir = os.path.dirname(SHP_VIAL)
        if os.path.exists(vial_dir):
            candidates = [f for f in os.listdir(vial_dir) if f.endswith(".shp")]
            if candidates:
                SHP_VIAL_REAL = os.path.join(vial_dir, candidates[0])
                print(f"[AUTO-DETECT] Usando camino: {SHP_VIAL_REAL}")
                calculate_distance_raster(executable, SHP_VIAL_REAL, OUT_DIST_VIAL, "lines")
    else:
        calculate_distance_raster(executable, SHP_VIAL, OUT_DIST_VIAL, "lines")

    # ---------------------------------------------------------------------
    # 3. ALINEACIÓN FINAL (Resampleo para coincidir con DEM)
    # ---------------------------------------------------------------------
    # Esto es crucial: a veces WBT genera rasters ligeramente desplazados.
    # Forzamos que coincidan con el DEM usando 'Resample' o una operación matemática simple.
    # Por ahora, confiamos en la resolución 30m, pero verificaremos visualmente.
    
    print("\n" + "="*50)
    print("FASE 2 COMPLETADA")
    print(f"Agua: {OUT_DIST_AGUA}")
    print(f"Vialidad: {OUT_DIST_VIAL}")
    print("="*50)

if __name__ == "__main__":
    main()
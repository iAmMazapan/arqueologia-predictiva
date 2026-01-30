"""
PROYECTO: Modelo Predictivo de Riesgo Arqueológico
MODULO: 01_preproc_geomorfologia_v2.py

ESTRATEGIA HÍBRIDA:
1. Ingeniería de Datos (Geopandas): Conversión precisa de Líneas -> Puntos conservando 'Z'.
2. Procesamiento (Whitebox): Interpolación TIN y Variables Derivadas.

Standard: 30m resolution, EPSG:32719.
"""

import os
import sys
import subprocess
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import whitebox

# --- CONFIGURACIÓN ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
RAW_PATH = os.path.join(BASE_DIR, "data", "raw")
PROC_PATH = os.path.join(BASE_DIR, "data", "processed")

if not os.path.exists(PROC_PATH):
    os.makedirs(PROC_PATH)

# Inputs y Outputs
INPUT_CURVAS = os.path.join(RAW_PATH, "27s-curvas.shp")
TEMP_POINTS = os.path.join(PROC_PATH, "temp_vertices_z.shp") # Nuevo nombre
DEM_TIF = os.path.join(PROC_PATH, "raster_dem.tif")
SLOPE_TIF = os.path.join(PROC_PATH, "raster_pendiente.tif")
TRI_TIF = os.path.join(PROC_PATH, "raster_rugosidad.tif")

# Parámetros
Z_FIELD = "Z"           
SPATIAL_RES = 30.0

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
    wbt = whitebox.WhiteboxTools()
    return wbt.exe_path

def prepare_points_with_geopandas():
    """
    Función Crítica: Convierte líneas a puntos asegurando que la columna Z se mantenga.
    Reemplaza a ExtractNodes que estaba fallando al perder atributos.
    """
    print(f"[PANDAS] Leyendo {os.path.basename(INPUT_CURVAS)}...")
    try:
        gdf_lines = gpd.read_file(INPUT_CURVAS)
        
        # Verificación de seguridad
        if Z_FIELD not in gdf_lines.columns:
            print(f"[ERROR CRÍTICO] La columna '{Z_FIELD}' no existe en el Shapefile.")
            print(f"Columnas disponibles: {gdf_lines.columns.tolist()}")
            return False

        print("[PANDAS] Extrayendo vértices y clonando atributos (esto puede tomar un momento)...")
        
        # Estrategia vectorizada para explotar coordenadas (mucho más rápido que iterar)
        # 1. Extraemos todas las coordenadas de cada línea
        # 2. Mantenemos el índice para cruzar con los datos originales
        
        # Convertimos geometrías a una lista de puntos
        points_list = []
        z_values = []
        
        # Iteramos (es necesario para extraer coords complejas)
        # Optimizacion: Usamos list comprehension que es más veloz en Python
        for idx, row in gdf_lines.iterrows():
            geom = row.geometry
            z_val = row[Z_FIELD]
            
            if geom.geom_type == 'LineString':
                coords = list(geom.coords)
                points_list.extend([Point(xy) for xy in coords])
                z_values.extend([z_val] * len(coords))
            elif geom.geom_type == 'MultiLineString':
                for part in geom.geoms:
                    coords = list(part.coords)
                    points_list.extend([Point(xy) for xy in coords])
                    z_values.extend([z_val] * len(coords))
        
        print(f"[PANDAS] Creando GeoDataFrame de Puntos ({len(points_list)} vértices)...")
        gdf_points = gpd.GeoDataFrame(
            {Z_FIELD: z_values}, 
            geometry=points_list,
            crs=gdf_lines.crs
        )
        
        print(f"[PANDAS] Guardando {os.path.basename(TEMP_POINTS)}...")
        gdf_points.to_file(TEMP_POINTS)
        return True

    except Exception as e:
        print(f"[ERROR PANDAS] Falló la conversión: {e}")
        return False

def main():
    executable = find_whitebox_binary()
    print(f"[SISTEMA] Motor Whitebox: {executable}")

    # ---------------------------------------------------------------------
    # PASO 1: Preparación de Datos (Geopandas)
    # ---------------------------------------------------------------------
    # Solo ejecutamos si no existe el archivo o si queremos forzarlo
    if not os.path.exists(TEMP_POINTS):
        if not prepare_points_with_geopandas():
            return
    else:
        print("[INFO] Usando archivo de puntos existente.")

    # ---------------------------------------------------------------------
    # PASO 2: Interpolación TIN (Whitebox)
    # ---------------------------------------------------------------------
    print("[WHITEBOX] Ejecutando Interpolación TIN...")
    
    # Ahora usamos TEMP_POINTS que GARANTIZADO tiene la columna "Z"
    cmd_tin = [
        executable,
        "--run=TINGridding",
        f"--input={TEMP_POINTS}",
        f"--output={DEM_TIF}",
        f"--field={Z_FIELD}",      
        "--use_z=False",            
        f"--resolution={SPATIAL_RES}",
        "-v"
    ]
    
    try:
        subprocess.run(cmd_tin, check=True)
    except subprocess.CalledProcessError:
        print("[ERROR] Falló TINGridding. Revisa el log arriba.")
        return

    # ---------------------------------------------------------------------
    # PASO 3: Variables Derivadas
    # ---------------------------------------------------------------------
    if os.path.exists(DEM_TIF):
        print("[WHITEBOX] Generando Pendiente y Rugosidad...")
        
        # Slope
        subprocess.run([executable, "--run=Slope", f"--dem={DEM_TIF}", f"--output={SLOPE_TIF}", "--units=degrees"], check=False)
        
        # TRI
        subprocess.run([executable, "--run=RuggednessIndex", f"--dem={DEM_TIF}", f"--output={TRI_TIF}"], check=False)

        print("\n" + "="*50)
        print("¡MISIÓN CUMPLIDA! FASE 1 COMPLETADA")
        print("="*50)
        print(f"Archivos listos en: {PROC_PATH}")
    else:
        print(f"[ERROR CRÍTICO] {DEM_TIF} no aparece en disco.")

if __name__ == "__main__":
    main()
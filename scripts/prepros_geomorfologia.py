"""
PROYECTO: Modelo Predictivo de Riesgo Arqueológico
MODULO: preproc_geomorfologia.py

DESCRIPCIÓN: 
Pipeline de procesamiento de terreno.
1. Valida integridad de Shapefiles.
2. Convierte Curvas de Nivel (Líneas) -> Vértices (Puntos).
3. Genera DEM (TIN Gridding).
4. Calcula Pendiente y Rugosidad.

[cite_start]Standard: 30m resolution, EPSG:32719[cite: 17].
"""

import os
import sys
import subprocess
import whitebox

# --- FUNCIONES DE SOPORTE ---

def find_whitebox_binary():
    """Localiza el binario ejecutable de WhiteboxTools robustamente."""
    module_dir = os.path.dirname(whitebox.__file__)
    possible_paths = [
        os.path.join(module_dir, "WBT", "whitebox_tools"),
        os.path.join(module_dir, "whitebox_tools"),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            if sys.platform != "win32":
                try:
                    os.chmod(path, 0o755)
                except:
                    pass
            return path
    wbt = whitebox.WhiteboxTools()
    return wbt.exe_path

def check_shapefile_integrity(shp_path):
    """Verifica que existan .shp, .shx y .dbf."""
    base = os.path.splitext(shp_path)[0]
    required = ['.shp', '.shx', '.dbf']
    missing = []
    
    print(f"[AUDITORÍA] Verificando: {os.path.basename(shp_path)}")
    for ext in required:
        # Verifica extensión exacta o mayúsculas (Linux sensitive)
        if not (os.path.exists(base + ext) or os.path.exists(base + ext.upper())):
            print(f"  [FALTA] {ext}")
            missing.append(ext)
    
    if missing:
        print(f"[ERROR CRÍTICO] Shapefile corrupto o incompleto. Faltan: {missing}")
        return False
    print("  [OK] Integridad validada.")
    return True

def run_wbt_command(executable, tool_name, args):
    """Ejecuta un comando de Whitebox controlando errores."""
    cmd = [executable, f"--run={tool_name}"] + args + ["-v"]
    print(f"[EJECUTANDO] {tool_name}...")
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[FALLO] {tool_name} terminó con código de error {e.returncode}.")
        return False

# --- PROCESO PRINCIPAL ---

def main():
    # 1. Configuración de Rutas
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.dirname(SCRIPT_DIR)
    RAW_PATH = os.path.join(BASE_DIR, "data", "raw")
    PROC_PATH = os.path.join(BASE_DIR, "data", "processed")

    if not os.path.exists(PROC_PATH):
        os.makedirs(PROC_PATH)

    # Inputs
    INPUT_CURVAS = os.path.join(RAW_PATH, "27s-curvas.shp")
    
    # Intermedios (Archivos temporales)
    TEMP_POINTS = os.path.join(PROC_PATH, "temp_vertices.shp")
    
    # Outputs Finales
    DEM_TIF = os.path.join(PROC_PATH, "raster_dem.tif")
    SLOPE_TIF = os.path.join(PROC_PATH, "raster_pendiente.tif")
    TRI_TIF = os.path.join(PROC_PATH, "raster_rugosidad.tif")
    
    # [cite_start]Parámetros [cite: 17, 16]
    Z_FIELD = "Z"           
    SPATIAL_RES = 30.0

    # Validaciones Previas
    if not check_shapefile_integrity(INPUT_CURVAS):
        return
    
    executable = find_whitebox_binary()
    print(f"[SISTEMA] Motor Whitebox en: {executable}")

    # ---------------------------------------------------------------------
    # PASO 1.5: Conversión de Líneas a Puntos (El paso que faltaba)
    # ---------------------------------------------------------------------
    # TINGridding solo acepta puntos. Extraemos los vértices de las curvas.
    if not os.path.exists(TEMP_POINTS):
        success = run_wbt_command(executable, "LinesToPoints", [ # O 'VerticesToPoints'
            f"--input={INPUT_CURVAS}",
            f"--output={TEMP_POINTS}"
        ])
        # Nota: Si LinesToPoints falla, intentaremos VerticesToPoints (nombres varian por versión)
        if not success:
            print("[INTENTO 2] Probando herramienta alternativa 'VerticesToPoints'...")
            if not run_wbt_command(executable, "VerticesToPoints", [
                f"--input={INPUT_CURVAS}",
                f"--output={TEMP_POINTS}"
            ]):
                print("[ABORTAR] No se pudieron extraer los puntos de las líneas.")
                return
    else:
        print("[INFO] Puntos temporales ya existen. Saltando conversión.")

    # ---------------------------------------------------------------------
    # PASO 2: Interpolación TIN (TINGridding)
    # ---------------------------------------------------------------------
    # Ahora usamos TEMP_POINTS (puntos) en lugar de INPUT_CURVAS (líneas)
    
    # Nota Importante: Al convertir líneas a puntos, los atributos se mantienen.
    # Usamos use_z=False para obligarlo a leer la columna "Z" de la tabla.
    
    success_tin = run_wbt_command(executable, "TINGridding", [
        f"--input={TEMP_POINTS}",
        f"--output={DEM_TIF}",
        f"--field={Z_FIELD}",
        "--use_z=False", 
        f"--resolution={SPATIAL_RES}"
    ])

    if not success_tin or not os.path.exists(DEM_TIF):
        print("[ERROR] El DEM no se generó.")
        return

    # ---------------------------------------------------------------------
    # PASO 3: Variables Derivadas (Pendiente y Rugosidad)
    # ---------------------------------------------------------------------
    print("[INFO] Generando variables geomorfológicas...")

    # [cite_start]Pendiente [cite: 21]
    run_wbt_command(executable, "Slope", [
        f"--dem={DEM_TIF}",
        f"--output={SLOPE_TIF}",
        "--units=degrees"
    ])

    # [cite_start]Rugosidad (TRI) [cite: 24]
    run_wbt_command(executable, "RuggednessIndex", [
        f"--dem={DEM_TIF}",
        f"--output={TRI_TIF}"
    ])

    # Limpieza opcional (descomentar si quieres borrar el temporal)
    # try: os.remove(TEMP_POINTS); os.remove(TEMP_POINTS.replace(".shp", ".shx")); os.remove(TEMP_POINTS.replace(".shp", ".dbf"))
    # except: pass

    print(f"\n[ÉXITO TOTAL] Procesamiento finalizado.\nArchivos generados en: {PROC_PATH}")

if __name__ == "__main__":
    main()
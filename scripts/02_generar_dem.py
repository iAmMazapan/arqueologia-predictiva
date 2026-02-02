import sys
import os
import time
from pathlib import Path
from osgeo import gdal

# Esto es clave en Windows para que la terminal refresque la barra de progreso
os.environ['PYTHONUNBUFFERED'] = '1'

# Configuración de Rutas con Pathlib (Crucial para compatibilidad Windows/Linux)
BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_VECTOR = BASE_DIR / "data" / "processed" / "curvas_unificadas_19s.gpkg"
OUTPUT_DEM = BASE_DIR / "data" / "processed" / "raster_dem_30m.tif"

# Asegurar que la carpeta existe antes de escribir
OUTPUT_DEM.parent.mkdir(parents=True, exist_ok=True)

gdal.UseExceptions()

def crear_dem_windows():
    if not INPUT_VECTOR.exists():
        print(f"❌ Error: No se encuentra el archivo en {INPUT_VECTOR}")
        return

    print(f"🚀 Iniciando Proceso en Windows...")
    print(f"📊 Datos: 132 Millones de puntos.")
    
    # 1. Abrir Vector y obtener extensión
    ds_vector = gdal.OpenEx(str(INPUT_VECTOR))
    layer = ds_vector.GetLayer(0)
    x_min, x_max, y_min, y_max = layer.GetExtent()

    # 2. Calcular dimensiones para resolución 30m
    ancho_px = int((x_max - x_min) / 30)
    alto_px = int((y_max - y_min) / 30)

    print(f"📐 Tamaño del Raster: {ancho_px} x {alto_px} píxeles")
    
    # 3. Configuración de la Interpolación
    # En Windows, 'callback=gdal.TermProgress' es lo más estable para ver 0...10...100
    grid_opts = gdal.GridOptions(
        format="GTiff",
        outputType=gdal.GDT_Float32,
        algorithm="invdist:power=2.0:smoothing=1.0:radius1=500:radius2=500",
        zfield="Z",
        width=ancho_px,
        height=alto_px,
        outputBounds=[x_min, y_max, x_max, y_min],
        callback=gdal.TermProgress
    )

    start_time = time.time()
    try:
        print("⏳ Fase 1: Cargando índice espacial... (Esto toma tiempo, no cierres la ventana)")
        
        # Ejecución principal
        gdal.Grid(str(OUTPUT_DEM), str(INPUT_VECTOR), options=grid_opts)
        
        duracion = (time.time() - start_time) / 3600
        print(f"\n✅ PROCESO COMPLETADO EN {duracion:.2f} HORAS")
        print(f"📂 Archivo generado: {OUTPUT_DEM}")

    except Exception as e:
        print(f"\n❌ Error Crítico: {e}")
    finally:
        ds_vector = None # Liberar archivo

if __name__ == "__main__":
    crear_dem_windows()
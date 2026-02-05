import os
import glob
from osgeo import gdal

# --- CONFIGURACIÓN AUTOMÁTICA ---
# Detectamos dónde está este script (carpeta /scripts)
dir_actual = os.path.dirname(os.path.abspath(__file__))

# Buscamos la carpeta de datos justo al lado
CARPETA_DATOS = os.path.join(dir_actual, "ASTER_GDEM_PERU_OFICIAL")

# Definimos el nombre del archivo final dentro de esa misma carpeta
ARCHIVO_SALIDA = os.path.join(CARPETA_DATOS, "DEM_PERU_ALBERS_30M_FINAL.tif")

# Configuración del Plan Maestro
SRC_DESTINO = 'ESRI:102033'  # South America Albers Equal Area
PIXEL_SIZE = 30              # 30 Metros

def fusionar_y_reproyectar():
    print(f"{'='*60}")
    print(f"MOTOR PYTHON: Fusión y Reproyección")
    print(f"Fuente: {CARPETA_DATOS}")
    print(f"Target: Albers (102033) a 30m")
    print(f"{'='*60}")

    # 1. Buscar los TIFs extraídos (los que dicen _dem.tif)
    # Buscamos recursivamente por si 7zip creó subcarpetas
    patron = os.path.join(CARPETA_DATOS, "**", "*dem.tif")
    lista_tifs = glob.glob(patron, recursive=True)
    
    # Filtramos para asegurarnos que son archivos reales
    lista_tifs = [f for f in lista_tifs if os.path.isfile(f)]

    if not lista_tifs:
        print("❌ ERROR CRÍTICO: No se encontraron archivos '*dem.tif'.")
        print("   Verifica que la extracción del paso anterior funcionó.")
        return

    print(f"✓ Se encontraron {len(lista_tifs)} cuadrantes DEM listos.")

    # 2. Crear Mosaico Virtual (VRT)
    # Esto une los 136 archivos en memoria sin ocupar espacio en disco
    print("\n2. Construyendo Mosaico Virtual (VRT)...")
    vrt_path = os.path.join(CARPETA_DATOS, "temp_mosaico.vrt")
    
    # srcNodata=None permite que GDAL lea el valor nulo original del archivo
    vrt_options = gdal.BuildVRTOptions(resampleAlg='cubic', srcNodata=None)
    gdal.BuildVRT(vrt_path, lista_tifs, options=vrt_options)
    print("   -> Estructura VRT creada.")

    # 3. Warping (La Transformación Final)
    print(f"\n3. Generando archivo final (esto tomará unos minutos)...")
    
    warp_options = gdal.WarpOptions(
        format='GTiff',
        dstSRS=SRC_DESTINO,      # Proyección Albers
        xRes=PIXEL_SIZE,         # 30m
        yRes=PIXEL_SIZE,         # 30m
        resampleAlg='bilinear',  # Bilineal es mejor para mantener la suavidad del terreno
        dstNodata=-9999,         # Valor para zonas vacías
        creationOptions=[
            "COMPRESS=LZW",      # Compresión sin pérdida (vital)
            "TILED=YES",         # Lectura rápida
            "BIGTIFF=YES",       # Soporte para archivos >4GB
            "NUM_THREADS=ALL_CPUS", # Usa toda la potencia de tu PC
            "PREDICTOR=2"        # Optimiza compresión de elevación
        ]
    )

    try:
        gdal.Warp(ARCHIVO_SALIDA, vrt_path, options=warp_options)
        print(f"\n✅ ¡ÉXITO! Archivo guardado en:")
        print(f"   {ARCHIVO_SALIDA}")
    except Exception as e:
        print(f"\n❌ Error durante el procesamiento: {e}")

    # Limpieza del archivo temporal
    if os.path.exists(vrt_path):
        os.remove(vrt_path)

if __name__ == "__main__":
    fusionar_y_reproyectar()
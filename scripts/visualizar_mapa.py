import os
from osgeo import gdal
import matplotlib.pyplot as plt
import numpy as np

# --- CONFIGURACIÓN ---
# Detectamos la ruta automáticamente (igual que antes)
dir_actual = os.path.dirname(os.path.abspath(__file__))
# Ruta a tu archivo final generado
archivo_dem = os.path.join(dir_actual, "ASTER_GDEM_PERU_OFICIAL", "DEM_PERU_ALBERS_30M_FINAL.tif")

def visualizar_dem():
    print(f"Abriendo archivo: {archivo_dem}")
    
    if not os.path.exists(archivo_dem):
        print("❌ ERROR: No encuentro el archivo TIF. Verifica la ruta.")
        return

    # 1. Abrir con GDAL
    ds = gdal.Open(archivo_dem)
    if ds is None:
        print("❌ Error al abrir el archivo.")
        return

    banda = ds.GetRasterBand(1)
    nodata = banda.GetNoDataValue()
    
    # Obtener dimensiones reales
    cols = ds.RasterXSize
    rows = ds.RasterYSize
    print(f"Dimensiones originales: {cols} x {rows} píxeles")

    # 2. ESTRATEGIA DE MEMORIA: DOWNSAMPLING
    # No leemos todos los píxeles. Leemos 1 de cada 20 píxeles.
    # Esto reduce el peso en RAM de 4GB a unos 10MB para la gráfica.
    factor_reduccion = 20  
    
    nuevo_w = cols // factor_reduccion
    nuevo_h = rows // factor_reduccion
    
    print(f"Generando vista previa ({nuevo_w} x {nuevo_h})...")
    
    # Leemos los datos redimensionados al vuelo
    data = banda.ReadAsArray(buf_xsize=nuevo_w, buf_ysize=nuevo_h)

    # 3. Limpieza de Datos (Enmascarar los bordes negros)
    # Convertimos el valor NoData (-9999) en "nan" (invisible) para que no se vea feo
    if nodata is not None:
        data_masked = np.ma.masked_equal(data, nodata)
    else:
        data_masked = data

    # 4. Graficar con Matplotlib
    print("Renderizando gráfico...")
    plt.figure(figsize=(12, 10)) # Tamaño de la imagen
    
    # cmap='terrain' es una paleta de colores especial para topografía (azul-verde-café-blanco)
    img = plt.imshow(data_masked, cmap='terrain') 
    
    plt.colorbar(img, label='Elevación (m.s.n.m.)')
    plt.title(f'Modelo de Elevación Digital - Perú (Albers 30m)\nVista Previa {100/factor_reduccion}% Res.')
    plt.xlabel('Coordenada X (Proyectada)')
    plt.ylabel('Coordenada Y (Proyectada)')
    
    # Guardar en disco
    ruta_imagen = os.path.join(dir_actual, "mapa_peru_preview.png")
    plt.savefig(ruta_imagen, dpi=150)
    print(f"✅ Imagen guardada en: {ruta_imagen}")
    
    # Mostrar en pantalla (solo si tienes interfaz gráfica activa)
    plt.show()

    # Limpieza
    ds = None

if __name__ == "__main__":
    visualizar_dem()
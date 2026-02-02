import geopandas as gpd
import pandas as pd
import os
from pathlib import Path
from glob import glob

# 1. Configuración de Rutas Relativas al Script
# Path(__file__).resolve() nos da la ruta absoluta de este archivo .py
BASE_DIR = Path(__file__).resolve().parent.parent
RUTA_ENTRADA = BASE_DIR / "data" / "raw" / "curvas_de_altura_peru"
RUTA_SALIDA = BASE_DIR / "data" / "processed"

# Crear carpeta de salida si no existe
RUTA_SALIDA.mkdir(parents=True, exist_ok=True)

def consolidar_datasets():
    print(f"🔍 Buscando archivos en: {RUTA_ENTRADA}")
    
    # Buscamos todos los .shp recursivamente
    archivos = glob(str(RUTA_ENTRADA / "**" / "*.shp"), recursive=True)
    
    if not archivos:
        print("❌ Error: No se encontraron archivos .shp en la ruta especificada.")
        return
    
    print(f"📦 Se encontraron {len(archivos)} archivos. Iniciando unificación...")
    
    lista_gdfs = []
    
    for i, path in enumerate(archivos):
        try:
            gdf = gpd.read_file(path)
            if gdf.empty: continue

            # Forzar UTM 19S para asegurar el 30x30m posterior
            gdf = gdf.to_crs(epsg=32719)

            # Prioridad absoluta a la columna 'ALTITUD'
            col_z = 'ALTITUD' if 'ALTITUD' in gdf.columns else None
            
            # Si no se llama ALTURA, buscamos alternativas comunes del IGN
            if not col_z:
                col_z = next((c for c in gdf.columns if c.upper() in ['Z', 'COTA', 'ELEV']), None)
            
            if col_z:
                subset = gdf[[col_z, 'geometry']].rename(columns={col_z: 'Z'})
                lista_gdfs.append(subset)
                print(f"[{i+1}] ✅ Procesado: {Path(path).name} (usando {col_z})")
            else:
                print(f"[{i+1}] ⚠️ Columna 'ALTURA' no encontrada en {Path(path).name}")

        except Exception as e:
            print(f"❌ Error en {Path(path).name}: {e}")

    if lista_gdfs:
        print("\n🔄 Fusionando capas... (esto puede tardar según tu RAM)")
        dataset_final = gpd.GeoDataFrame(pd.concat(lista_gdfs, ignore_index=True), crs="EPSG:32719")
        
        output_file = RUTA_SALIDA / "curvas_unificadas_19s.gpkg"
        print(f"💾 Guardando en: {output_file}")
        
        # GeoPackage es superior a SHP para grandes volúmenes de datos
        dataset_final.to_file(output_file, driver="GPKG")
        
        print(f"\n🚀 ¡LISTO! Total de elementos unificados: {len(dataset_final)}")
        return len(dataset_final)
    
    return 0

if __name__ == "__main__":
    consolidar_datasets()
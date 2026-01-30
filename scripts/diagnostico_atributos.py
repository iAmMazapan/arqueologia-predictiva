"""
DIAGNÓSTICO DE ATRIBUTOS
Este script lee el archivo temporal de puntos y nos muestra
qué columnas existen realmente para dejar de adivinar el nombre.
"""
import os
import geopandas as gpd

def main():
    # Ruta absoluta al archivo generado
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    shp_path = os.path.join(base_dir, "data", "processed", "temp_vertices.shp")
    
    print(f"Inspeccionando: {shp_path}")
    
    if not os.path.exists(shp_path):
        print("[ERROR] El archivo no existe. Ejecuta primero el preproc_geomorfologia.")
        return

    try:
        # Leemos el archivo
        gdf = gpd.read_file(shp_path)
        
        print("\n" + "="*40)
        print("COLUMNAS ENCONTRADAS:")
        print("="*40)
        print(gdf.columns.tolist())
        
        print("\n" + "="*40)
        print("PRIMERAS 5 FILAS (MUESTRA):")
        print("="*40)
        print(gdf.head())
        
        print("\n" + "="*40)
        print("GEOMETRÍA:")
        print("="*40)
        # Verificamos si es 3D (PointZ) o 2D (Point)
        print(f"Tipo de Geometría: {gdf.geom_type.unique()}")
        print(f"¿Tiene coordenadas Z?: {gdf.has_z.any()}")

    except Exception as e:
        print(f"[ERROR] No se pudo leer el archivo: {e}")

if __name__ == "__main__":
    main()
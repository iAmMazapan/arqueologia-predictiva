import requests
import json
import os
import time
import re

# --- CONFIGURACIÓN DE ARQUITECTO ---
URL_OBJETIVO = "https://geogpsperu.github.io/dem.github.com/data/DEMASTER_3.js"
CARPETA_SALIDA = "ASTER_GDEM_PERU_OFICIAL"

print(f"{'='*80}")
print(f"SISTEMA DE DESCARGA: ASTER GDEM (Fuente: GeoGPSPeru)")
print(f"{'='*80}")

if not os.path.exists(CARPETA_SALIDA):
    os.makedirs(CARPETA_SALIDA)

def limpiar_y_parsear_js(texto_js):
    """
    Truco técnico: Convierte el archivo .js (variable javascript) en JSON puro para Python.
    Elimina 'var json_DEMASTER_3 = ' del inicio y posibles ';' del final.
    """
    try:
        # 1. Buscamos dónde empieza el primer corchete '{'
        indice_inicio = texto_js.find('{')
        if indice_inicio == -1: return None
        
        # 2. Cortamos todo lo anterior (el 'var ... = ')
        json_str = texto_js[indice_inicio:]
        
        # 3. Limpiamos basura del final (punto y coma, espacios)
        json_str = json_str.strip().rstrip(';')
        
        # 4. Parseamos
        return json.loads(json_str)
    except Exception as e:
        print(f"Advertencia de Parsing: {e}. Intentando método Regex alternativo...")
        return None

def obtener_enlaces_regex(texto):
    """Método de respaldo por si el JSON falla"""
    patron = r'"codigo":\s*"([^"]+)",\s*"descarga":\s*"(https:[^"]+)"'
    coincidencias = re.findall(patron, texto)
    # Convertimos a lista de diccionarios para mantener formato
    return [{'properties': {'codigo': c[0], 'descarga': c[1]}} for c in coincidencias]

def convertir_url_gdrive(url):
    """Transforma el link de visualización en link de descarga directa"""
    # Maneja urls con caracteres escapados '\/' que vienen en el JSON
    url = url.replace('\\/', '/')
    
    file_id = None
    if 'id=' in url:
        file_id = url.split('id=')[1].split('&')[0]
    elif '/file/d/' in url:
        file_id = url.split('/file/d/')[1].split('/')[0]
    
    if file_id:
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url

def ejecutar_mision():
    print(f"1. Obteniendo catálogo desde: {URL_OBJETIVO}")
    try:
        resp = requests.get(URL_OBJETIVO)
        resp.raise_for_status()
        contenido = resp.text
        
        # Intentamos parsear como JSON primero (más elegante)
        datos = limpiar_y_parsear_js(contenido)
        
        lista_archivos = []
        if datos and 'features' in datos:
            lista_archivos = datos['features']
            print("   -> Método JSON exitoso.")
        else:
            # Si falla, usamos Regex (fuerza bruta)
            print("   -> Método JSON falló, activando extracción Regex.")
            lista_archivos = obtener_enlaces_regex(contenido)

        total = len(lista_archivos)
        print(f"2. Se identificaron {total} cuadrantes para descargar.\n")
        
        for i, item in enumerate(lista_archivos, 1):
            prop = item.get('properties', {})
            # Si usamos regex, la estructura ya viene directa, si es JSON viene anidada
            if 'codigo' not in prop: prop = item # Ajuste por si viene del regex
            
            codigo = prop.get('codigo', f"SIN_CODIGO_{i}")
            url_raw = prop.get('descarga', '')
            
            if not url_raw: continue

            nombre_archivo = f"{codigo}.zip" # Ejemplo: S19W70.zip
            ruta_final = os.path.join(CARPETA_SALIDA, nombre_archivo)
            url_descarga = convertir_url_gdrive(url_raw)

            print(f"[{i}/{total}] Procesando {codigo}...", end=" ", flush=True)

            if os.path.exists(ruta_final):
                print("✓ Ya existe.")
                continue

            try:
                r = requests.get(url_descarga, stream=True)
                if r.status_code == 200:
                    with open(ruta_final, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print("✓ Descargado.")
                else:
                    print(f"✗ Error HTTP {r.status_code}")
            except Exception as e:
                print(f"✗ Falló: {e}")

            # Pausa táctica
            time.sleep(0.5)

    except Exception as e:
        print(f"\nError Crítico: {e}")

if __name__ == "__main__":
    ejecutar_mision()
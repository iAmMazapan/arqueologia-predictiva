"""
UTILIDAD DE DIAGNÓSTICO: WhiteboxTools Capability Scanner.

Este script audita la instalación local del motor WhiteboxTools para identificar
los nombres exactos de las herramientas disponibles. Es crítico para resolver
discrepancias de versiones (ej. 'LinesToPoints' vs 'ExtractNodes').

Uso:
    python3 scripts/diagnostico_tools.py
"""

import os
import sys
import subprocess
import whitebox

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
                try: os.chmod(path, 0o755)
                except: pass
            return path
    return whitebox.WhiteboxTools().exe_path

def main():
    executable = find_whitebox_binary()
    print(f"[SISTEMA] Binario encontrado en: {executable}")
    
    # Palabras clave para buscar herramientas de conversión vectorial
    keywords = ["Vertices", "Points", "Nodes", "Convert"]
    
    print("-" * 60)
    print("BUSCANDO HERRAMIENTAS DE CONVERSIÓN DISPONIBLES")
    print("-" * 60)
    
    for kw in keywords:
        print(f"\n>> Buscando herramientas con la palabra clave: '{kw}'")
        try:
            # Ejecutamos con --listtools para ver qué hay instalado realmente
            subprocess.run([executable, "--listtools", kw], check=False)
        except Exception as e:
            print(f"Error ejecutando búsqueda: {e}")

if __name__ == "__main__":
    main()
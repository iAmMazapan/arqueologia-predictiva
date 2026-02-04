#!/bin/bash

# --- CONFIGURACIÓN ---
# Ruta exacta de tus datos
CARPETA_DATOS="/home/mazapan/Documentos/arqueologia-predictiva/scripts/ASTER_GDEM_PERU_OFICIAL"
# Ruta exacta de tu script de Python (el de fusión que te pasé antes)
SCRIPT_PYTHON="/home/mazapan/Documentos/arqueologia-predictiva/scripts/03_fusionar_tifs.py"

echo "=========================================="
echo "   SISTEMA AUTOMATIZADO DE PROCESAMIENTO  "
echo "=========================================="

# 1. Ir a la carpeta de datos
cd "$CARPETA_DATOS" || { echo "❌ No encuentro la carpeta"; exit 1; }
echo "📂 Trabajando en: $(pwd)"

# 2. Descompresión Inteligente (Detecta si tienes 7z o unrar)
echo "🔨 Paso 1: Extrayendo archivos (RAR disfrazados de ZIP)..."

if command -v 7z &> /dev/null; then
    # 7-Zip es el mejor para esto, se come lo que sea
    # -y: dice sí a todo
    # -aos: salta si ya existe el archivo (ahorra tiempo)
    7z x "*.zip" -y -aos
elif command -v unrar &> /dev/null; then
    # Si no tienes 7z, usamos unrar
    for f in *.zip; do
        unrar x -o+ "$f" > /dev/null
    done
else
    echo "❌ ERROR CRÍTICO: No tienes instalado 'unrar' ni 'p7zip'."
    echo "   Instálalo con: sudo apt install p7zip-full"
    exit 1
fi

echo "✅ Extracción completada."

# 3. Ejecutar el script de Python para unir los TIFs
echo "🗺️  Paso 2: Uniendo TIFs y Reproyectando a Albers..."
# Verificamos si existe el script de python
if [ -f "$SCRIPT_PYTHON" ]; then
    python3 "$SCRIPT_PYTHON"
else
    echo "⚠️  No encuentro el script de Python en: $SCRIPT_PYTHON"
    echo "   (Asegúrate de guardar el código de Python que te di como '03_fusionar_tifs.py')"
fi

echo "=========================================="
echo "🏁  TODO LISTO. REVISA TU CARPETA."
echo "=========================================="

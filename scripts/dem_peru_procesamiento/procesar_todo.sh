#!/bin/bash

# --- CONFIGURACIÓN ---
# Ruta exacta de tus datos
CARPETA_DATOS="/home/mazapan/Documentos/arqueologia-predictiva/scripts/ASTER_GDEM_PERU_OFICIAL"
# Ruta exacta de tu script de Python (el de fusión que te pasé antes)
SCRIPT_PYTHON="/home/mazapan/Documentos/arqueologia-predictiva/scripts/fusionar_tifs.py"

echo "=========================================="
echo "   SISTEMA AUTOMATIZADO DE PROCESAMIENTO  "
echo "=========================================="

# 1. Ir a la carpeta de datos
cd "$CARPETA_DATOS" || { echo "❌ No encuentro la carpeta"; exit 1; }
echo "📂 Trabajando en: $(pwd)"

# 2. Descompresión con Barra de Progreso
echo "--------------------------------------------------"
echo "🔨 Paso 1: Extrayendo archivos (Modo Observabilidad)..."
echo "--------------------------------------------------"

# Contamos cuántos zips hay en total
total_files=$(ls *.zip 2>/dev/null | wc -l)
current=0

if [ "$total_files" -eq 0 ]; then
    echo "❌ No encontré archivos .zip en esta carpeta."
    exit 1
fi

# Detectamos el motor (7z o unrar)
if command -v 7z &> /dev/null; then
    MODE="7z"
elif command -v unrar &> /dev/null; then
    MODE="unrar"
else
    echo "❌ ERROR: Instala p7zip-full."
    exit 1
fi

echo "📦 Total de archivos a procesar: $total_files"

# Bucle archivo por archivo para mostrar progreso
for f in *.zip; do
    # Incrementamos contador
    current=$((current + 1))
    
    # Calculamos porcentaje
    percent=$((current * 100 / total_files))
    
    # Imprimimos estado sobre la misma línea (\r) para efecto de animación
    # Usamos printf para formatear bonito
    printf "\r⏳ Progreso: [%3d%%] - Archivo %3d de %3d: %s" "$percent" "$current" "$total_files" "$f"

    if [ "$MODE" = "7z" ]; then
        # -bso0: Silencia la salida estándar (para que no ensucie nuestra barra)
        # -y: Sí a todo
        7z x "$f" -y -aos -bso0 > /dev/null 2>&1
    else
        unrar x -o+ "$f" > /dev/null 2>&1
    fi
done

echo "" # Salto de línea final para limpiar
echo "✅ Extracción completada."

# 3. Ejecutar el script de Python para unir los TIFs
echo "🗺️  Paso 2: Uniendo TIFs y Reproyectando a Albers..."

# Verificamos si existe el script de python
if [ -f "$SCRIPT_PYTHON" ]; then
    python3 "$SCRIPT_PYTHON"
else
    echo "⚠️  No encuentro el script de Python en: $SCRIPT_PYTHON"
    echo "   (Asegúrate de guardar el código de Python que te di como 'fusionar_tifs.py')"
fi

echo "=========================================="
echo "    TODO LISTO. REVISA TU CARPETA."
echo "=========================================="

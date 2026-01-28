# IA Predictiva para Evaluación de Riesgo Arqueológico 🏛️🛰️

## Resumen del Proyecto
[cite_start]Este proyecto desarrolla un modelo de **Machine Learning (XGBoost)** diseñado para estimar la probabilidad matemática de presencia de restos arqueológicos en un área determinada[cite: 3, 65]. [cite_start]El sistema utiliza un enfoque de **"Rasterización Previa"** para optimizar el procesamiento de grandes volúmenes de datos geográficos de las Cartas Nacionales[cite: 4, 5].

## 🛠️ Metodología (Sprint 10 Días)
[cite_start]Basado en el **Plan Maestro de Riesgo Arqueológico**[cite: 2]:

1. [cite_start]**Ingesta de Datos:** Scripts automatizados para la descarga y unificación de Cartas Nacionales (Vectores de ríos, curvas, etc.)[cite: 8, 27].
2. [cite_start]**Ingeniería de Características (Fase 1):** Generación de Rasters de Elevación (DEM), Pendiente, Rugosidad (TRI) y Mapas de Proximidad (Euclidean Distance) en QGIS[cite: 7, 19, 26].
3. [cite_start]**Sampling y Extracción (Fase 2):** Script de "taladrado" para crear el dataset de entrenamiento (`Clase 1` vs `Clase 0`)[cite: 47, 50, 53].
4. [cite_start]**Modelado (Fase 3):** Entrenamiento de un clasificador binario con lógica probabilística[cite: 61, 76].
5. [cite_start]**Inferencia (Fase 4):** Evaluación de archivos KMZ para determinar el nivel de riesgo (Bajo, Medio, Alto)[cite: 83, 94].

## 📂 Estructura del Repositorio
* `src/00_ingesta/`: Scripts de descarga (`requests`) y unificación de capas (`geopandas`).
* `src/01_features/`: Procesamiento de Rasters y extracción de valores.
* `data/`: (No incluido en el repo por peso) Contiene `raw`, `intermediate` y `processed`.
* [cite_start]`models/`: Modelos entrenados en formato JSON[cite: 79].

## 🚀 Cómo ejecutar
1. Clonar el repositorio.
2. Instalar dependencias: `pip install -r requirements.txt`.
3. Ejecutar scripts de ingesta en `src/00_ingesta/`.
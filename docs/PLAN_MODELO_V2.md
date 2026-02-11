# Plan de Mejora del Modelo Predictivo Arqueológico
## De la versión 1 (línea base) a un modelo publicable

**Proyecto:** Modelo Predictivo de Potencial Arqueológico — Perú  
**Fecha:** 11 de febrero de 2026  
**Autor:** Yishar Piero Nieto Barrientos  
**Dirigido a:** Equipo de dirección del proyecto

---

## 1. ¿Dónde estamos hoy?

En **2 semanas de trabajo intensivo** se construyó la primera versión del modelo (v1), que incluye:

- Descarga y procesamiento del Modelo Digital de Elevación (DEM) de todo el Perú a 30 metros de resolución (~20 cuadrantes fusionados).
- Obtención y limpieza de capas vectoriales: red hídrica, lagos, Qhapaq Ñan y sitios arqueológicos del Ministerio de Cultura.
- Reproyección de todas las capas a un sistema de coordenadas unificado (Albers 102033).
- Cálculo de 7 variables predictoras (rasters de distancia + pendiente).
- Extracción de un dataset de entrenamiento con ~27,000 muestras.
- Entrenamiento y evaluación de 3 algoritmos (Random Forest, XGBoost, Regresión Logística).

### Resultado actual

| Métrica | Valor |
|---------|:-----:|
| Precisión global (Random Forest) | 91% |
| AUC-ROC | 0.970 |
| F1-Score | 0.92 |

Estos números parecen buenos, pero tienen **un problema de fondo** que impide su publicación.

---

## 2. ¿Por qué el modelo actual no es publicable?

### El diagnóstico en términos simples

El modelo aprendió **dónde** hay sitios arqueológicos, pero no aprendió **por qué** los humanos eligieron esos lugares.

Las variables que más pesan en la decisión del modelo son:

| Variable | Peso |
|----------|:----:|
| Distancia a Núcleos Monumentales (G1) | 30.8% |
| Distancia a Paisajes Culturales (G2) | 18.7% |
| Distancia a Evidencias Puntuales (G3) | 17.9% |
| Distancia al Qhapaq Ñan | 15.5% |
| **Subtotal: proximidad a sitios conocidos** | **82.9%** |
| Pendiente + ríos + lagos (variables ambientales) | 17.1% |

Esto significa que el modelo dice: *"hay sitios arqueológicos cerca de donde ya hay sitios arqueológicos"*. En estadística espacial esto se llama **autocorrelación**, y cualquier revisor de una revista científica lo rechazaría porque es un razonamiento circular.

### ¿Qué necesitamos?

Agregar **variables ambientales y geográficas** que representen las razones reales por las que las civilizaciones prehispánicas eligieron ciertos lugares: acceso a agua, posición estratégica en el terreno, control visual del territorio, acceso a múltiples recursos, etc.

---

## 3. ¿Por qué esto no se hace en una semana?

### Analogía para no ingenieros

Construir un modelo predictivo es como construir una casa:

- **Los datos son los cimientos.** Si están torcidos, toda la casa se cae. No se puede acelerar el fraguado del concreto solo porque hay prisa.
- **El algoritmo es solo el techo.** Es la parte más rápida, pero no sirve de nada si los cimientos están mal.

En este proyecto, el **60–80% del tiempo total** se invierte en obtener, limpiar y preparar los datos. Esto no es ineficiencia: es un estándar reconocido en la industria del Machine Learning (Kaggle ML & DS Survey, 2023).

### ¿Qué implica concretamente agregar una variable nueva?

Cada variable nueva requiere **6 pasos obligatorios**, sin atajos:

```
┌─────────────────────────────────────────────────────────┐
│  1. OBTENCIÓN         Buscar la fuente, descargar       │
│  2. INSPECCIÓN        Verificar calidad, detectar       │
│                       errores, datos faltantes           │
│  3. REPROYECCIÓN      Convertir al sistema de           │
│                       coordenadas del proyecto           │
│                       (cada fuente viene diferente)      │
│  4. RASTERIZACIÓN     Convertir de vectores a píxeles   │
│                       de 30×30 metros                    │
│  5. ALINEACIÓN        Asegurar que cada píxel de la     │
│                       nueva capa coincida exactamente    │
│                       con los píxeles de todas las       │
│                       demás capas (si hay 1 metro de     │
│                       desfase, el modelo lee datos       │
│                       falsos)                            │
│  6. VALIDACIÓN        Verificar que los valores          │
│                       resultantes tengan sentido         │
│                       geográfico y estadístico           │
└─────────────────────────────────────────────────────────┘
```

En la v1, este proceso se aplicó a 7 capas y tomó **2 semanas corriendo**. Para la v2 necesitamos aplicarlo a 6–12 capas nuevas, varias de fuentes externas.

---

## 4. Plan de trabajo propuesto

### Bloque 1 — Variables derivadas del DEM (ya disponible)

Estas variables se calculan matemáticamente a partir del modelo de elevación que ya tenemos. No requieren datos externos nuevos.

| # | Variable | ¿Qué mide? | ¿Por qué importa arqueológicamente? | Tiempo |
|:-:|----------|-------------|--------------------------------------|:------:|
| 1 | Altitud / Pisos ecológicos | Altura sobre el nivel del mar, clasificada en regiones naturales | Los asentamientos se distribuyen según pisos ecológicos (costa, quechua, puna), cada uno con estrategias de subsistencia distintas | 1.5 días |
| 2 | Aspecto (orientación solar) | Hacia dónde "mira" la ladera (norte, sur, este, oeste) | En el hemisferio sur, las laderas orientadas al norte reciben más sol. Las viviendas prehispánicas preferían estas orientaciones | 1 día |
| 3 | Curvatura del terreno | Si el terreno es cóncavo (cuenca), convexo (cresta) o plano | Identifica terrazas naturales aptas para construcción vs. crestas expuestas | 1 día |
| 4 | TPI (Posición Topográfica) | Si un punto está en un valle, ladera, cresta o espolón respecto a su entorno | Identifica cimas y espolones (sitios defensivos) y fondos de valle (sitios agrícolas). Directamente señalado en el feedback arqueológico | 2 días |
| 5 | TWI (Humedad Topográfica) | Dónde se acumula el agua en el terreno según la forma del relieve | Proxy de disponibilidad de agua sin necesitar datos hidrológicos adicionales. El agua es el factor #1 del urbanismo prehispánico | 2 días |

| | **Subtotal Bloque 1** | | | **~8 días** |
|:-:|:-:|:-:|:-:|:-:|

> **Incluye:** cálculo + validación visual + integración al dataset + reentrenamiento del modelo.

---

### Bloque 2 — Variables con datos externos abiertos

Requieren descargar, limpiar y procesar datasets de instituciones peruanas o internacionales.

| # | Variable | Fuente | ¿Por qué importa? | Tiempo |
|:-:|----------|--------|-------------------|:------:|
| 6 | Ecotonos (bordes entre ecosistemas) | ESA WorldCover (acceso libre, 10m resolución) | Los asentamientos se ubican en la frontera entre dos ecosistemas para acceder a recursos de ambos | 3–4 días |
| 7 | Distancia a confluencias de ríos | Red hídrica ANA / HydroSHEDS | Las confluencias son puntos estratégicos de control territorial y acceso a agua | 2–3 días |
| 8 | Pasos de montaña (abras) | Derivado del DEM con análisis topográfico avanzado | Puntos de control obligatorio en las rutas costa–sierra | 3–4 días |
| 9 | Litología (tipo de roca) | Mapa Geológico del INGEMMET | Proximidad a canteras de piedra, recurso clave para construcción monumental | 2–3 días |

| | **Subtotal Bloque 2** | | | **~10–14 días** |
|:-:|:-:|:-:|:-:|:-:|

---

### Bloque 3 — Variables avanzadas (selectivo, si hay tiempo)

| # | Variable | Complejidad | Tiempo |
|:-:|----------|:-----------:|:------:|
| 10 | Análisis de visibilidad (viewshed) | Alta — computacionalmente pesado | 5–7 días |
| 11 | Clasificación geomorfológica (terrazas, conos aluviales) | Alta — requiere criterio experto | 5–7 días |
| 12 | Proximidad a manantiales/puquios | Media — depende de disponibilidad de datos | 4–5 días |

| | **Subtotal Bloque 3** | | **~14–19 días** |
|:-:|:-:|:-:|:-:|

---

## 5. Escenarios y recomendación

| Escenario | Alcance | Tiempo | ¿Publicable? |
|-----------|---------|:------:|:------------:|
| **A — Mínimo viable** | Bloque 1 solamente (5 variables nuevas del DEM) | 2 semanas | Parcialmente. Mejora el modelo pero puede ser insuficiente para una revista indexada |
| **B — Recomendado** | Bloque 1 + Bloque 2 (9 variables nuevas) | 4–5 semanas | **Sí.** Modelo robusto con variables ambientales genuinas. Competitivo para publicación |
| **C — Ideal** | Bloques 1 + 2 + selección del 3 | 6–8 semanas | Sí, con análisis diferenciadores (visibilidad, geomorfología) |

### Mi recomendación: Escenario B

Con ~12 variables ambientales bien procesadas, el modelo tendría fundamento ambiental y arqueológico sólido. Las variables de proximidad a sitios conocidos (G1, G2, G3) pasarían de ser el 83% del peso a ser un complemento, no la base del modelo.

---

## 6. ¿Qué pasa si se apura?

| Si se acelera... | Consecuencia |
|-------------------|-------------|
| Se saltan validaciones de alineación | El modelo lee valores de píxeles equivocados → resultados no reproducibles |
| Se omite la inspección de datos externos | Errores topológicos o valores nulos contaminan el dataset sin ser detectados |
| Se meten todas las variables sin análisis de correlación | Multicolinealidad → el modelo se confunde con variables redundantes y pierde capacidad predictiva |
| Se entrena sin validación cruzada rigurosa | Overfitting → el modelo parece perfecto en pruebas pero falla en zonas nuevas |

**En ciencia de datos, un modelo mal hecho es peor que no tener modelo.** Produce falsa confianza y decisiones incorrectas.

---

## 7. Compromiso

Me comprometo a:
- Entregar avances semanales con métricas verificables.
- Documentar cada variable nueva con su fuente, método de cálculo y validación.
- Mantener un código reproducible y organizado para la publicación.
- Comunicar inmediatamente cualquier bloqueo técnico o de datos.

Solo pido el tiempo necesario para hacer un trabajo que resista el escrutinio de una revisión científica.

---

*"Without data cleaning, the most sophisticated algorithm is just an expensive random number generator."*  
— Principio fundamental de Machine Learning aplicado

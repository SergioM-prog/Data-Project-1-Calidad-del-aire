📖 EXPLICACIÓN DETALLADA DEL CÓDIGO
🏗️ PARTE 1: CONFIGURACIÓN Y CONTEXTO

-- STAGING: Limpieza de datos de Valencia
--
-- ¿Qué hace?
-- Selecciona y renombra las columnas de la tabla raw.valencia_air
-- para tener nombres consistentes en inglés
--
-- NOTA IMPORTANTE: La tabla raw.valencia_air tiene columnas estructuradas
-- (NO es JSONB). El backend FastAPI ya validó y estructuró los datos.
¿Qué son estos comentarios?

Son explicaciones para que tú (y otros desarrolladores) entiendan qué hace este archivo
Explican que la tabla raw.valencia_air ya tiene columnas separadas (no JSON)
Esto significa que tu Backend FastAPI ya hizo el trabajo de validar y estructurar los datos
⚙️ PARTE 2: CONFIGURACIÓN DBT

{{ config(materialized='view') }}
¿Qué hace esto?

Le dice a dbt: "Crea esto como una VISTA (view), no como una tabla"
¿Qué es una vista?

Una vista es como una "consulta guardada" que se ejecuta cada vez que la consultas
NO ocupa espacio en disco (no duplica datos)
Siempre muestra datos actualizados de la tabla original
Alternativa:

Si pones materialized='table' → Crea una tabla real (duplica los datos, ocupa espacio)
¿Por qué usamos 'view' aquí?

Porque staging solo renombra columnas, no hace cálculos pesados
No tiene sentido duplicar los datos si solo estamos cambiando nombres
🆔 PARTE 3: IDENTIFICADORES BÁSICOS

SELECT
    -- Identificadores básicos
    objectid AS station_id,
    nombre AS station_name,
¿Qué hace esto?

Toma la columna objectid de la tabla raw y la renombra a station_id
Toma la columna nombre de la tabla raw y la renombra a station_name
¿Por qué renombrar?

Para tener nombres consistentes en inglés en todo el proyecto
objectid → station_id (más claro que es un ID de estación)
nombre → station_name (estándar en inglés)
Ejemplo de resultado:

objectid (antes)	nombre (antes)	→	station_id (después)	station_name (después)
43038001	Viveros	→	43038001	Viveros
43038004	Pista Silla	→	43038004	Pista Silla
🌫️ PARTE 4: CONTAMINANTES

    -- Contaminantes (ya vienen como NUMERIC de la tabla raw, los convertimos a FLOAT)
    no2::FLOAT AS no2,
    pm10::FLOAT AS pm10,
    so2::FLOAT AS so2,
    o3::FLOAT AS o3,
    co::FLOAT AS co,
    pm25::FLOAT AS pm25,
¿Qué hace esto?

Toma cada columna de contaminante de la tabla raw
Las convierte de tipo NUMERIC a tipo FLOAT usando ::FLOAT
¿Por qué convertir a FLOAT?

NUMERIC es más preciso pero más lento para cálculos
FLOAT es más rápido para promedios, sumas, y operaciones matemáticas
Como son mediciones de sensores (no dinero), FLOAT es suficiente
Ejemplo de conversión:

Columna raw	Tipo en raw	→	Columna staging	Tipo en staging
no2 = 42.5	NUMERIC	→	no2 = 42.5	FLOAT
pm25 = 8.3	NUMERIC	→	pm25 = 8.3	FLOAT
¿Qué significan estos contaminantes?

NO2 (Dióxido de nitrógeno): Tráfico vehicular
PM10 (Partículas gruesas): Polvo, construcción
PM2.5 (Partículas finas): Combustión, humo (muy peligrosas para salud)
SO2 (Dióxido de azufre): Industrias, combustión de carbón
O3 (Ozono troposférico): Reacciones químicas con luz solar
CO (Monóxido de carbono): Combustión incompleta de vehículos
🏷️ PARTE 5: METADATOS Y CALIDAD

    -- Metadatos y calidad del aire
    calidad_am AS air_quality_status,
¿Qué hace esto?

Renombra calidad_am (calidad ambiente en español) a air_quality_status (inglés)
¿Qué valores tiene esta columna?

Ejemplos: "Buena", "Moderada", "Pobre", "Muy Pobre", etc.
Es una clasificación textual de la calidad del aire
Ejemplo:

calidad_am (antes)	→	air_quality_status (después)
Buena	→	Buena
Moderada	→	Moderada
📍 PARTE 6: UBICACIÓN GEOGRÁFICA

    -- Ubicación geográfica
    direccion AS address,
    tipozona AS zone_type,
    tipoemisio AS emission_type,
¿Qué hace esto?

Renombra columnas de ubicación al inglés:
direccion → address (dirección física de la estación)
tipozona → zone_type (tipo de zona: urbana, suburbana, rural)
tipoemisio → emission_type (tipo de emisión: tráfico, fondo, industrial)
Ejemplo:

direccion (antes)	tipozona (antes)	→	address (después)	zone_type (después)
Avda. de Cataluña	Urbana	→	Avda. de Cataluña	Urbana
🗺️ PARTE 7: COORDENADAS GEOGRÁFICAS (JSONB)

    -- Coordenadas geográficas (extraer del JSONB geo_point_2d)
    (geo_point_2d->>'lat')::FLOAT AS latitud,
    (geo_point_2d->>'lon')::FLOAT AS longitud,
¿Qué hace esto?

La columna geo_point_2d es un JSONB que contiene: {"lat": 39.4742, "lon": -0.3764}
Usamos el operador ->> para extraer los valores del JSON
Los convertimos a FLOAT para poder usarlos en mapas
Explicación del operador ->>:

geo_point_2d->>'lat' significa: "Del JSON geo_point_2d, dame el valor de la clave 'lat' como texto"
::FLOAT lo convierte de texto a número decimal
Ejemplo:

geo_point_2d (antes)	→	latitud (después)	longitud (después)
{"lat": "39.4742", "lon": "-0.3764"}	→	39.4742	-0.3764
¿Para qué sirve esto?

Para crear mapas con la ubicación exacta de cada estación
Para calcular distancias entre estaciones
Para hacer análisis geoespaciales
⏰ PARTE 8: MARCAS DE TIEMPO (TIMESTAMPS)

    -- Timestamps (marcas de tiempo)
    fecha_carg AS measure_timestamp,
    ingested_at,
¿Qué hace esto?

fecha_carg → measure_timestamp: Momento en que se tomó la medición (de la API)
ingested_at → ingested_at: Momento en que guardamos el dato en nuestra base de datos
Diferencia importante:

measure_timestamp: Cuándo el sensor midió la contaminación (ej: 2026-01-20 14:30:00)
ingested_at: Cuándo nosotros guardamos ese dato (ej: 2026-01-20 14:31:15)
¿Por qué guardar ambos?

Para detectar retrasos en la ingesta de datos
Para saber si los datos son en "tiempo real" o históricos
🔑 PARTE 9: IDS INTERNOS Y METADATOS

    -- ID interno de la fila en la tabla raw
    id AS raw_id,

    -- Otros campos útiles
    parametros AS parametros_medidos,
    mediciones AS mediciones_texto,
    fiwareid AS fiware_id
¿Qué hace esto?

id → raw_id: ID autoincremental de PostgreSQL (único por fila)
parametros → parametros_medidos: Lista de parámetros que mide esta estación
mediciones → mediciones_texto: Texto con las mediciones en formato string
fiwareid → fiware_id: ID del sistema FIWARE (estándar europeo de smart cities)
¿Para qué sirve el raw_id?

Para poder hacer "trazabilidad": saber qué fila de raw originó este dato
Para debugging: si hay un error, puedes volver a la fila original
📊 PARTE 10: ORIGEN DE LOS DATOS

FROM {{ source('air_quality', 'valencia_air') }}
¿Qué hace esto?

Le dice a dbt: "Lee los datos de la tabla valencia_air del schema raw"
{{ source('air_quality', 'valencia_air') }} es sintaxis de dbt para referenciar tablas
¿Qué es source?

Es una función de dbt que busca la tabla en el archivo de configuración sources.yml
Permite que dbt sepa de qué tabla depende esta vista
Equivalente en SQL normal:


FROM raw.valencia_air
🔍 PARTE 11: FILTRO DE DATOS VÁLIDOS

-- Filtrar solo registros con timestamp válido
WHERE fecha_carg IS NOT NULL
¿Qué hace esto?

Elimina filas donde fecha_carg es NULL (vacío)
Solo toma registros que tienen una fecha/hora de medición válida
¿Por qué filtrar?

Porque sin timestamp no sabemos cuándo se midió el contaminante
Datos sin fecha son inútiles para análisis temporales (gráficas de evolución)
Ejemplo de lo que se filtra:

objectid	nombre	pm25	fecha_carg	¿Se incluye?
43038001	Viveros	8.5	2026-01-20 14:30	✅ SÍ
43038002	Pista Silla	12.3	NULL	❌ NO (filtrado)

🎯 RESUMEN VISUAL: ¿QUÉ HACE ESTE CÓDIGO?

TABLA RAW (raw.valencia_air)          VISTA STAGING (stg_valencia_air)
┌────────────────────────────┐        ┌────────────────────────────┐
│ objectid = 43038001        │   →    │ station_id = 43038001      │
│ nombre = "Viveros"         │   →    │ station_name = "Viveros"   │
│ no2 = 42.5 (NUMERIC)       │   →    │ no2 = 42.5 (FLOAT)         │
│ pm25 = 8.3 (NUMERIC)       │   →    │ pm25 = 8.3 (FLOAT)         │
│ direccion = "Avda. Cat."   │   →    │ address = "Avda. Cat."     │
│ geo_point_2d = {"lat":...} │   →    │ latitud = 39.4742          │
│                            │   →    │ longitud = -0.3764         │
│ fecha_carg = 2026-01-20... │   →    │ measure_timestamp = ...    │
└────────────────────────────┘        └────────────────────────────┘
         (español)                              (inglés)
    (tipos variados)                      (tipos optimizados)
    
✅ AHORA EJECUTA:

docker-compose exec dbt dbt run
Deberías ver:


1 of 4 OK created sql view model staging.stg_valencia_air ... [CREATE VIEW in 0.10s]
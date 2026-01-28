-- int_air_quality_union.sql

WITH combined_data AS (
    -- 1. Datos reales: Marcados como 'real' y con prioridad 1
    SELECT 
        *,
        'real' AS origen,
        1 AS prioridad 
    FROM {{ ref('stg_valencia_air') }}

    UNION ALL

    -- 2. Datos simulados: Marcados como 'simulated' y con prioridad 2
    SELECT 
        *,
        'simulated' AS origen,
        2 AS prioridad 
    FROM {{ ref('stg_valencia_air_historical_simulated_hourly') }}
),

deduplicated AS (
    -- 3. Identificamos duplicados (misma estación y hora) priorizando el dato 'real'
    SELECT 
        *,
        ROW_NUMBER() OVER (
            PARTITION BY id_estacion, fecha_hora_medicion 
            ORDER BY prioridad ASC
        ) AS fila_numero
    FROM combined_data
)

-- 4. Selección final con la nueva columna 'origen'
SELECT 
    id_estacion,
    nombre_estacion,
    'Valencia' AS ciudad,
    origen, -- <--- Nueva columna de trazabilidad
    no2,
    pm10,
    so2,
    o3,
    co,
    pm25,
    estado_calidad_aire,
    direccion,
    tipo_zona,
    tipo_emision,
    latitud,
    longitud,
    fecha_hora_medicion,
    fecha_ingesta,
    fiware_id
FROM deduplicated
WHERE fila_numero = 1
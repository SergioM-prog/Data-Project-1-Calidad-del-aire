-- TABLA: Dimensión de Estaciones (Catálogo de estaciones de medición)
-- 
-- ¿Qué hace esta tabla?

-- Crea un registro único por cada estación de medición con información resumida:
-- - Cuántas veces ha medido
-- - Cuándo fue su primera y última medición
-- - En qué ciudad está
--
-- ¿Para qué sirve?

-- Para hacer gráficas de:

    -- - Mapa de estaciones activas
    -- - Listado de estaciones más activas
    -- - Filtros por ciudad

{{ config(materialized='table') }}

SELECT DISTINCT

    -- Identificadores únicos de la estación

    station_id AS id_estacion,
    station_name AS nombre_estacion,
    'Valencia' AS ciudad,
    
    -- Estadísticas de actividad de la estación

    MIN(measure_timestamp) AS primera_medicion,
    MAX(measure_timestamp) AS ultima_medicion,
    COUNT(*) AS total_mediciones,
    
    -- Días de diferencia entre primera y última medición

    DATE_PART('day', MAX(measure_timestamp) - MIN(measure_timestamp)) AS dias_activa

FROM {{ ref('stg_valencia_air') }}

-- Agrupamos por estación para tener una fila por estación

GROUP BY station_id, station_name

-- Ordenamos por las estaciones más activas primero

ORDER BY total_mediciones DESC
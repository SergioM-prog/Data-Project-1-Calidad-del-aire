-- TABLA: Ranking de Estaciones por Contaminación
-- 
-- ¿Qué hace esta tabla?
-- Calcula el PROMEDIO de cada contaminante por estación
-- en los últimos 30 días y las ORDENA (ranking)
--
-- ¿Para qué sirve?
-- Para gráficas de:
-- - Top 10 estaciones con peor calidad de aire
-- - Comparar estaciones entre sí
-- - Identificar zonas problemáticas de la ciudad
--
-- Se actualiza cada vez que corre dbt (cada 5 minutos)

{{ config(materialized='table') }}

WITH estadisticas_estacion AS (
    -- Subconsulta: Calculamos promedios de los últimos 30 días
    SELECT 
        station_id AS id_estacion,
        station_name AS nombre_estacion,
        
        -- Promedios de cada contaminante (redondeados a 2 decimales)
        ROUND(AVG(pm25)::numeric, 2) AS promedio_pm25,
        ROUND(AVG(pm10)::numeric, 2) AS promedio_pm10,
        ROUND(AVG(no2)::numeric, 2) AS promedio_no2,
        ROUND(AVG(so2)::numeric, 2) AS promedio_so2,
        ROUND(AVG(o3)::numeric, 2) AS promedio_ozono,
        ROUND(AVG(co)::numeric, 2) AS promedio_co,
        
        -- Máximos registrados (picos de contaminación)
        ROUND(MAX(pm25)::numeric, 2) AS maximo_pm25,
        ROUND(MAX(pm10)::numeric, 2) AS maximo_pm10,
        ROUND(MAX(no2)::numeric, 2) AS maximo_no2,
        
        -- Contamos cuántas mediciones tiene cada estación
        COUNT(*) AS total_mediciones
        
    FROM {{ ref('stg_valencia_air') }}
    
    -- Solo últimos 30 días
    WHERE measure_timestamp >= CURRENT_DATE - INTERVAL '30 days'
    
    GROUP BY station_id, station_name
)

SELECT 
    *,
    
    -- Rankings individuales (1 = la más contaminada, 20 = la menos contaminada)
    RANK() OVER (ORDER BY promedio_pm25 DESC) AS ranking_pm25,
    RANK() OVER (ORDER BY promedio_pm10 DESC) AS ranking_pm10,
    RANK() OVER (ORDER BY promedio_no2 DESC) AS ranking_no2,
    RANK() OVER (ORDER BY promedio_so2 DESC) AS ranking_so2,
    RANK() OVER (ORDER BY promedio_ozono DESC) AS ranking_ozono,
    
    -- Índice compuesto de contaminación general
    -- (promedio de los 3 rankings principales dividido por 3)
    ROUND((
        RANK() OVER (ORDER BY promedio_pm25 DESC) + 
        RANK() OVER (ORDER BY promedio_pm10 DESC) + 
        RANK() OVER (ORDER BY promedio_no2 DESC)
    )::numeric / 3.0, 1) AS ranking_general,
    
    -- Clasificación textual según ranking general
    CASE
        WHEN ROUND((
            RANK() OVER (ORDER BY promedio_pm25 DESC) + 
            RANK() OVER (ORDER BY promedio_pm10 DESC) + 
            RANK() OVER (ORDER BY promedio_no2 DESC)
        )::numeric / 3.0, 1) <= 3 THEN 'Zona Muy Contaminada'
        WHEN ROUND((
            RANK() OVER (ORDER BY promedio_pm25 DESC) + 
            RANK() OVER (ORDER BY promedio_pm10 DESC) + 
            RANK() OVER (ORDER BY promedio_no2 DESC)
        )::numeric / 3.0, 1) <= 7 THEN 'Zona Contaminada'
        WHEN ROUND((
            RANK() OVER (ORDER BY promedio_pm25 DESC) + 
            RANK() OVER (ORDER BY promedio_pm10 DESC) + 
            RANK() OVER (ORDER BY promedio_no2 DESC)
        )::numeric / 3.0, 1) <= 12 THEN 'Zona Moderada'
        ELSE 'Zona Limpia'
    END AS clasificacion_zona

FROM estadisticas_estacion

-- Ordenamos por el promedio de PM2.5 (el más peligroso para la salud)
ORDER BY promedio_pm25 DESC
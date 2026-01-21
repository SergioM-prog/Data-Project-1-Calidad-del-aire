-- TABLA: Calidad del Aire - Resumen Semanal
-- 
-- ¿Qué hace esta tabla?
-- Agrupa TODAS las mediciones por SEMANAS (lunes a domingo)
-- y calcula promedios, máximos y mínimos de cada contaminante
--
-- ¿Para qué sirve?
-- Para gráficas de:
-- - Evolución de contaminación por semanas (tendencias largas)
-- - Comparar esta semana vs semana pasada
-- - Ver patrones estacionales (verano vs invierno)
--
-- Diferencia con fct_air_quality_daily:
-- Esta es SEMANAL (7 días agrupados), la otra es DIARIA (1 día)

{{ config(materialized='table') }}

SELECT
    -- Fecha de inicio de la semana (siempre lunes)
    DATE_TRUNC('week', measure_timestamp) AS inicio_semana,
    
    -- Fecha de fin de la semana (domingo)
    DATE_TRUNC('week', measure_timestamp) + INTERVAL '6 days' AS fin_semana,
    
    -- Número de semana del año (1-52)
    EXTRACT(WEEK FROM measure_timestamp) AS numero_semana,
    
    -- Año
    EXTRACT(YEAR FROM measure_timestamp) AS año,
    
    -- Identificadores de estación
    station_id AS id_estacion,
    station_name AS nombre_estacion,
    
    -- PROMEDIOS semanales de cada contaminante
    ROUND(AVG(no2)::numeric, 2) AS promedio_semanal_no2,
    ROUND(AVG(pm10)::numeric, 2) AS promedio_semanal_pm10,
    ROUND(AVG(pm25)::numeric, 2) AS promedio_semanal_pm25,
    ROUND(AVG(so2)::numeric, 2) AS promedio_semanal_so2,
    ROUND(AVG(o3)::numeric, 2) AS promedio_semanal_ozono,
    ROUND(AVG(co)::numeric, 2) AS promedio_semanal_co,
    
    -- MÁXIMOS de la semana (picos de contaminación)
    ROUND(MAX(pm25)::numeric, 2) AS maximo_pm25_semana,
    ROUND(MAX(pm10)::numeric, 2) AS maximo_pm10_semana,
    ROUND(MAX(no2)::numeric, 2) AS maximo_no2_semana,
    
    -- MÍNIMOS de la semana (días más limpios)
    ROUND(MIN(pm25)::numeric, 2) AS minimo_pm25_semana,
    ROUND(MIN(pm10)::numeric, 2) AS minimo_pm10_semana,
    ROUND(MIN(no2)::numeric, 2) AS minimo_no2_semana,
    
    -- Conteo de mediciones en esa semana (debería ser ~168 por estación si hay datos cada hora)
    COUNT(*) AS total_mediciones_semana,
    
    -- Días con datos completos en la semana
    COUNT(DISTINCT DATE(measure_timestamp)) AS dias_con_datos,
    
    -- Calidad promedio de la semana según PM2.5
    CASE 
        WHEN AVG(pm25) <= 10 THEN 'Semana Buena'
        WHEN AVG(pm25) <= 15 THEN 'Semana Moderada'
        WHEN AVG(pm25) <= 25 THEN 'Semana Pobre'
        ELSE 'Semana Muy Contaminada'
    END AS clasificacion_semana

FROM {{ ref('stg_valencia_air') }}

-- Agrupamos por semana y por estación
GROUP BY 
    DATE_TRUNC('week', measure_timestamp), 
    EXTRACT(WEEK FROM measure_timestamp),
    EXTRACT(YEAR FROM measure_timestamp),
    station_id, 
    station_name

-- Ordenamos de la semana más reciente a la más antigua
ORDER BY inicio_semana DESC, nombre_estacion

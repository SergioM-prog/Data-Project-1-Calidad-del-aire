-- TABLA: Calidad del Aire - Detalle Horario Completo
-- 
-- ¿Qué hace esta tabla?
-- Toma TODOS los registros de la vista staging y los guarda limpios
-- con TODOS los contaminantes en una sola fila
--
-- ¿Para qué sirve?
-- Para gráficas detalladas de:
-- - Evolución hora por hora de cualquier contaminante
-- - Comparar múltiples contaminantes al mismo tiempo
-- - Filtrar por estación específica y ver su historial completo
--
-- Diferencia con fct_air_quality_hourly:
-- Esta tabla es MÁS DETALLADA, la otra agrega promedios por hora

{{ config(materialized='table') }}

SELECT
    -- Marcas de tiempo
    measure_timestamp AS fecha_hora_medicion,
    DATE_TRUNC('hour', measure_timestamp) AS hora_agrupada,
    DATE(measure_timestamp) AS fecha,
    EXTRACT(HOUR FROM measure_timestamp) AS hora_del_dia,
    EXTRACT(DOW FROM measure_timestamp) AS dia_semana, -- 0=Domingo, 6=Sábado
    
    -- Identificadores de estación
    station_id AS id_estacion,
    station_name AS nombre_estacion,
    
    -- TODOS los contaminantes (en microgramos por metro cúbico)
    no2 AS dioxido_nitrogeno,    -- Viene del Tráfico vehicular principalmente
    pm10 AS particulas_gruesas,  -- Es Polvo, construcción
    pm25 AS particulas_finas,    -- Combustión, muy peligrosas para salud
    so2 AS dioxido_azufre,       -- Son residuos industriales y combustión de carbón
    o3 AS ozono,                 -- Reacciones químicas con luz solar
    co AS monoxido_carbono,      -- Combustión incompleta de vehículos
    
    -- Estado general de calidad del aire (texto descriptivo)
    air_quality_status AS estado_calidad_aire,
    
    -- Clasificación por nivel de contaminación PM2.5 (OMS 2021)
    CASE 
        WHEN pm25 <= 5 THEN 'Excelente'
        WHEN pm25 <= 10 THEN 'Buena'
        WHEN pm25 <= 15 THEN 'Moderada'
        WHEN pm25 <= 25 THEN 'Pobre'
        WHEN pm25 <= 35 THEN 'Muy Pobre'
        ELSE 'Peligrosa'
    END AS clasificacion_pm25,
    
    -- Clasificación por nivel de NO2 (OMS 2021)
    CASE 
        WHEN no2 <= 10 THEN 'Excelente'
        WHEN no2 <= 25 THEN 'Buena'
        WHEN no2 <= 40 THEN 'Moderada'
        WHEN no2 <= 50 THEN 'Pobre'
        ELSE 'Peligrosa'
    END AS clasificacion_no2

FROM {{ ref('stg_valencia_air') }}

-- Solo tomamos registros con timestamp válido (no nulos)
WHERE measure_timestamp IS NOT NULL

-- Ordenamos de más reciente a más antiguo
ORDER BY measure_timestamp DESC
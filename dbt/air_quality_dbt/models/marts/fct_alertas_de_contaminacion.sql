-- TABLA: Alertas de Contaminación
--
-- ¿Qué hace esta tabla?
-- Filtra SOLO los registros donde algún contaminante
-- superó los límites recomendados por la OMS (Organización Mundial de la Salud)
--
-- ¿Para qué sirve?
-- Para gráficas de:
-- - Historial de alertas (cuándo hubo contaminación peligrosa)
-- - Notificaciones en tiempo real
-- - Reportes de incidentes por zona
--
-- Límites de alerta usados (según OMS 2021):
-- - PM2.5: > 15 µg/m³ (promedio 24h)
-- - PM10: > 45 µg/m³ (promedio 24h)
-- - NO2: > 25 µg/m³ (promedio 24h)
-- - SO2: > 40 µg/m³ (promedio 24h)
-- - O3: > 100 µg/m³ (promedio 24h)
--
-- MEJORAS APLICADAS:
-- 1. Emojis y textos descriptivos removidos → Manejar en capa de presentación
-- 2. Lógica de severidad centralizada en CTE → DRY principle
-- 3. Lógica de contaminante_principal simplificada con GREATEST()

{{ config(materialized='table') }}

-- CTE 1: Tabla de configuración de severidad (Single Source of Truth)
WITH severidad_config AS (
    SELECT 1 AS nivel, 'LEVE' AS descripcion, 'Precaución para personas sensibles' AS recomendacion
    UNION ALL SELECT 2, 'MODERADO', 'Reducir actividad física intensa'
    UNION ALL SELECT 3, 'GRAVE', 'Grupos sensibles evitar actividad exterior'
    UNION ALL SELECT 4, 'CRÍTICO', 'Evitar salir'
),

-- CTE 2: Límites OMS configurables (fácil actualización cuando cambien estándares)
umbrales_oms AS (
    SELECT 'PM2.5' AS contaminante, 15.0 AS limite_leve, 25.0 AS limite_moderado, 35.0 AS limite_grave, 50.0 AS limite_critico
    UNION ALL SELECT 'PM10', 45.0, 70.0, 100.0, 150.0
    UNION ALL SELECT 'NO2', 25.0, 40.0, 50.0, 75.0
    UNION ALL SELECT 'SO2', 40.0, 60.0, 100.0, 150.0
    UNION ALL SELECT 'O3', 100.0, 140.0, 180.0, 240.0
),

-- CTE 3: Alertas base con cálculo de severidad
alertas_base AS (
    SELECT
        -- Marcas de tiempo
        measure_timestamp AS fecha_hora_alerta,
        DATE(measure_timestamp) AS fecha,
        EXTRACT(HOUR FROM measure_timestamp) AS hora,
        EXTRACT(DOW FROM measure_timestamp) AS dia_semana, -- 0=Domingo, 1=Lunes...

        -- Nombre del día en español
        CASE EXTRACT(DOW FROM measure_timestamp)
            WHEN 0 THEN 'Domingo'
            WHEN 1 THEN 'Lunes'
            WHEN 2 THEN 'Martes'
            WHEN 3 THEN 'Miércoles'
            WHEN 4 THEN 'Jueves'
            WHEN 5 THEN 'Viernes'
            WHEN 6 THEN 'Sábado'
        END AS nombre_dia,

        -- Identificadores
        station_id AS id_estacion,
        station_name AS nombre_estacion,

        -- Valores reales medidos
        ROUND(pm25::numeric, 2) AS valor_pm25,
        ROUND(pm10::numeric, 2) AS valor_pm10,
        ROUND(no2::numeric, 2) AS valor_no2,
        ROUND(so2::numeric, 2) AS valor_so2,
        ROUND(o3::numeric, 2) AS valor_o3,
        ROUND(co::numeric, 2) AS valor_co,

        -- Banderas booleanas de alerta (sin emojis ni textos)
        (pm25 > 15) AS tiene_alerta_pm25,
        (pm10 > 45) AS tiene_alerta_pm10,
        (no2 > 25) AS tiene_alerta_no2,
        (so2 > 40) AS tiene_alerta_so2,
        (o3 > 100) AS tiene_alerta_o3,

        -- Porcentaje de exceso sobre el límite OMS (para TODOS los contaminantes)
        ROUND(((pm25 / 15.0) - 1.0)::numeric * 100, 1) AS exceso_pm25_porcentaje,
        ROUND(((pm10 / 45.0) - 1.0)::numeric * 100, 1) AS exceso_pm10_porcentaje,
        ROUND(((no2 / 25.0) - 1.0)::numeric * 100, 1) AS exceso_no2_porcentaje,
        ROUND(((so2 / 40.0) - 1.0)::numeric * 100, 1) AS exceso_so2_porcentaje,
        ROUND(((o3 / 100.0) - 1.0)::numeric * 100, 1) AS exceso_o3_porcentaje,

        -- Nivel de severidad (centralizado, calculado una sola vez)
        CASE
            WHEN pm25 > 50 OR pm10 > 150 OR no2 > 75 OR so2 > 150 OR o3 > 240 THEN 4  -- CRÍTICO
            WHEN pm25 > 35 OR pm10 > 100 OR no2 > 50 OR so2 > 100 OR o3 > 180 THEN 3  -- GRAVE
            WHEN pm25 > 25 OR pm10 > 70 OR no2 > 40 OR so2 > 60 OR o3 > 140 THEN 2    -- MODERADO
            ELSE 1                                                                     -- LEVE
        END AS nivel_severidad,

        -- Contaminante principal (simplificado con GREATEST)
        -- Calculamos el ratio de exceso para cada contaminante y elegimos el mayor
        CASE
            WHEN pm25 / 15.0 = GREATEST(
                pm25 / 15.0,
                pm10 / 45.0,
                no2 / 25.0,
                COALESCE(so2 / 40.0, 0),
                COALESCE(o3 / 100.0, 0)
            ) THEN 'PM2.5'

            WHEN pm10 / 45.0 = GREATEST(
                pm25 / 15.0,
                pm10 / 45.0,
                no2 / 25.0,
                COALESCE(so2 / 40.0, 0),
                COALESCE(o3 / 100.0, 0)
            ) THEN 'PM10'

            WHEN no2 / 25.0 = GREATEST(
                pm25 / 15.0,
                pm10 / 45.0,
                no2 / 25.0,
                COALESCE(so2 / 40.0, 0),
                COALESCE(o3 / 100.0, 0)
            ) THEN 'NO2'

            WHEN so2 > 40 AND so2 / 40.0 = GREATEST(
                pm25 / 15.0,
                pm10 / 45.0,
                no2 / 25.0,
                so2 / 40.0,
                COALESCE(o3 / 100.0, 0)
            ) THEN 'SO2'

            WHEN o3 > 100 AND o3 / 100.0 = GREATEST(
                pm25 / 15.0,
                pm10 / 45.0,
                no2 / 25.0,
                COALESCE(so2 / 40.0, 0),
                o3 / 100.0
            ) THEN 'O3'

            ELSE 'MÚLTIPLE'
        END AS contaminante_principal

    FROM {{ ref('stg_valencia_air') }}

    -- FILTRO CRÍTICO: Solo registros que superan algún límite OMS
    WHERE
        pm25 > 15     -- Límite PM2.5 (OMS 2021)
        OR pm10 > 45  -- Límite PM10 (OMS 2021)
        OR no2 > 25   -- Límite NO2 (OMS 2021)
        OR so2 > 40   -- Límite SO2 (OMS 2021)
        OR o3 > 100   -- Límite O3 (OMS 2021)
)

-- SELECT FINAL: Join con tabla de severidad para obtener descripción y recomendación
SELECT
    a.*,
    s.descripcion AS descripcion_severidad,
    s.recomendacion
FROM alertas_base a
LEFT JOIN severidad_config s ON a.nivel_severidad = s.nivel

-- Ordenamos por las alertas más recientes primero y más severas primero
ORDER BY a.fecha_hora_alerta DESC, a.nivel_severidad DESC

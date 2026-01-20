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

{{ config(materialized='table') }}

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
    
    -- Tipo de alerta (puede haber varias simultáneas)
    CASE 
        WHEN pm25 > 15 THEN ' 🔴 ALERTA PM2.5 - Partículas finas peligrosas'
        ELSE NULL
    END AS alerta_pm25,
    
    CASE 
        WHEN pm10 > 45 THEN ' 🟠 ALERTA PM10 - Partículas gruesas elevadas'
        ELSE NULL
    END AS alerta_pm10,
    
    CASE 
        WHEN no2 > 25 THEN ' 🟡 ALERTA NO2 - Dióxido de nitrógeno alto'
        ELSE NULL
    END AS alerta_no2,
    
    CASE 
        WHEN so2 > 40 THEN ' 🟣 ALERTA SO2 - Dióxido de azufre elevado'
        ELSE NULL
    END AS alerta_so2,
    
    CASE 
        WHEN o3 > 100 THEN ' 🔵 ALERTA O3 - Ozono troposférico alto'
        ELSE NULL
    END AS alerta_o3,
    
    -- Valores reales medidos
    ROUND(pm25::numeric, 2) AS valor_pm25,
    ROUND(pm10::numeric, 2) AS valor_pm10,
    ROUND(no2::numeric, 2) AS valor_no2,
    ROUND(so2::numeric, 2) AS valor_so2,
    ROUND(o3::numeric, 2) AS valor_o3,
    ROUND(co::numeric, 2) AS valor_co,
    
    -- Porcentaje de exceso sobre el límite OMS
    ROUND(((pm25 / 15.0) - 1.0)::numeric * 100, 1) AS exceso_pm25_porcentaje,
    ROUND(((pm10 / 45.0) - 1.0)::numeric * 100, 1) AS exceso_pm10_porcentaje,
    ROUND(((no2 / 25.0) - 1.0)::numeric * 100, 1) AS exceso_no2_porcentaje,
    
    -- Nivel de severidad (1=leve, 2=moderado, 3=grave, 4=crítico)
    CASE
        WHEN pm25 > 50 OR pm10 > 150 OR no2 > 75 THEN 4  -- CRÍTICO
        WHEN pm25 > 35 OR pm10 > 100 OR no2 > 50 THEN 3  -- GRAVE
        WHEN pm25 > 25 OR pm10 > 70 OR no2 > 40 THEN 2   -- MODERADO
        ELSE 1                                            -- LEVE
    END AS nivel_severidad,
    
    -- Descripción textual del nivel
    CASE
        WHEN pm25 > 50 OR pm10 > 150 OR no2 > 75 THEN 'CRÍTICO - Evitar salir'
        WHEN pm25 > 35 OR pm10 > 100 OR no2 > 50 THEN 'GRAVE - Grupos sensibles evitar actividad exterior'
        WHEN pm25 > 25 OR pm10 > 70 OR no2 > 40 THEN 'MODERADO - Reducir actividad física intensa'
        ELSE 'LEVE - Precaución para personas sensibles'
    END AS recomendacion,
    
    -- Contaminante principal que causó la alerta
    CASE
        WHEN pm25 > 15 AND pm25/15.0 >= COALESCE(pm10/45.0, 0) AND pm25/15.0 >= COALESCE(no2/25.0, 0) THEN 'PM2.5'
        WHEN pm10 > 45 AND pm10/45.0 >= COALESCE(no2/25.0, 0) THEN 'PM10'
        WHEN no2 > 25 THEN 'NO2'
        WHEN so2 > 40 THEN 'SO2'
        WHEN o3 > 100 THEN 'O3'
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

-- Ordenamos por las alertas más recientes primero y más severas primero
ORDER BY measure_timestamp DESC, nivel_severidad DESC

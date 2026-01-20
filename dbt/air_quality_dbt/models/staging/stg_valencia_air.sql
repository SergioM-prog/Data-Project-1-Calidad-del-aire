-- WITH raw_data AS (
--     SELECT 
--         station_id,
--         data_raw,
--         timestamp AS ingested_at
--     FROM {{ source('air_quality', 'valencia_air') }}
-- )

-- SELECT
--     -- Identificadores básicos
--     station_id,
--     jsonb_extract_path_text(data_raw, 'nombre')::TEXT AS station_name,
    
--     -- Magnitudes (convertidas a FLOAT para poder hacer cálculos)
--     jsonb_extract_path_text(data_raw, 'no2')::FLOAT AS no2,
--     jsonb_extract_path_text(data_raw, 'pm10')::FLOAT AS pm10,
--     jsonb_extract_path_text(data_raw, 'so2')::FLOAT AS so2,
--     jsonb_extract_path_text(data_raw, 'o3')::FLOAT AS o3,
--     jsonb_extract_path_text(data_raw, 'co')::FLOAT AS co,
--     jsonb_extract_path_text(data_raw, 'pm25')::FLOAT AS pm25,

--     -- Metadatos y calidad
--     jsonb_extract_path_text(data_raw, 'calidad_am')::TEXT AS air_quality_status,
    
--     -- Timestamps (Convertimos el texto de la API a formato fecha real)
--     (jsonb_extract_path_text(data_raw, 'fecha_carg'))::TIMESTAMP WITH TIME ZONE AS measure_timestamp,
--     ingested_at,
    
--     -- Cambios hechos por Fran -- NUEVAS COLUMNAS 
    
--     -- Coordenadas geográficas (para mapas)
--     jsonb_extract_path_text(data_raw, 'latitud')::FLOAT AS latitud,
--     jsonb_extract_path_text(data_raw, 'longitud')::FLOAT AS longitud,
    
--     -- Ubicación
--     jsonb_extract_path_text(data_raw, 'municipio')::TEXT AS municipio,
--     jsonb_extract_path_text(data_raw, 'direccion')::TEXT AS direccion,
    
--     -- No se si son los metadatos correctos (si existen)
--     jsonb_extract_path_text(data_raw, 'tipo_estacion')::TEXT AS tipo_estacion,
--     jsonb_extract_path_text(data_raw, 'objectid')::TEXT AS objectid

-- FROM raw_data

-- STAGING: Limpieza de datos de Valencia
--
-- ¿Qué hace?
-- Selecciona y renombra las columnas de la tabla raw.valencia_air
-- para tener nombres consistentes en inglés
--
-- NOTA IMPORTANTE: La tabla raw.valencia_air tiene columnas estructuradas
-- (NO es JSONB). El backend FastAPI ya validó y estructuró los datos.

{{ config(materialized='view') }}

SELECT
    -- Identificadores básicos
    objectid AS station_id,
    nombre AS station_name,

    -- Contaminantes (ya vienen como NUMERIC de la tabla raw, los convertimos a FLOAT)
    no2::FLOAT AS no2,
    pm10::FLOAT AS pm10,
    so2::FLOAT AS so2,
    o3::FLOAT AS o3,
    co::FLOAT AS co,
    pm25::FLOAT AS pm25,

    -- Metadatos y calidad del aire
    calidad_am AS air_quality_status,

    -- Ubicación geográfica
    direccion AS address,
    tipozona AS zone_type,
    tipoemisio AS emission_type,

    -- Coordenadas geográficas (extraer del JSONB geo_point_2d)
    (geo_point_2d->>'lat')::FLOAT AS latitud,
    (geo_point_2d->>'lon')::FLOAT AS longitud,

    -- Timestamps (marcas de tiempo)
    fecha_carg AS measure_timestamp,
    ingested_at,

    -- ID interno de la fila en la tabla raw
    id AS raw_id,

    -- Otros campos útiles
    parametros AS parametros_medidos,
    mediciones AS mediciones_texto,
    fiwareid AS fiware_id

FROM {{ source('air_quality', 'valencia_air') }}

-- Filtrar solo registros con timestamp válido
WHERE fecha_carg IS NOT NULL


-- -- Cambios hechos por Fran: busca el markdown original arriba
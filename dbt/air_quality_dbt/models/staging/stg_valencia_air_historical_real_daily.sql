-- Staging para datos históricos REALES diarios de Valencia (2014-2025)
-- Fuente: CSV históricos cargados en raw.valencia_air_historical_real_daily

SELECT
    -- Identificadores básicos
    objectid AS id_estacion,
    nombre AS nombre_estacion,

    -- Contaminantes (convertimos NUMERIC a FLOAT para consistencia)
    no2::FLOAT AS no2,
    pm10::FLOAT AS pm10,
    so2::FLOAT AS so2,
    o3::FLOAT AS o3,
    co::FLOAT AS co,
    pm25::FLOAT AS pm25,

    -- Ubicación geográfica
    direccion,
    tipozona AS tipo_zona,
    tipoemisio AS tipo_emision,

    -- Coordenadas geográficas (extraer del JSONB geo_point_2d)
    (geo_point_2d->>'lat')::FLOAT AS latitud,
    (geo_point_2d->>'lon')::FLOAT AS longitud,

    -- Timestamps
    fecha_medicion AS fecha_hora_medicion,
    ingested_at AS fecha_ingesta,

    -- ID interno de la fila en la tabla raw
    id AS id_fila_raw,

    -- Identificador FIWARE
    fiwareid AS fiware_id

FROM {{ source('air_quality', 'valencia_air_historical_real_daily') }}

-- Filtrar solo registros con fecha válida
WHERE fecha_medicion IS NOT NULL

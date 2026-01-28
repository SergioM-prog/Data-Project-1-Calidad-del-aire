-- https://docs.getdbt.com/docs/build/materializations 

SELECT
    -- Identificadores básicos
    objectid AS id_estacion,
    nombre AS nombre_estacion,

    -- Contaminantes (ya vienen como NUMERIC de la tabla raw, los convertimos a FLOAT)
    no2::FLOAT AS no2,
    pm10::FLOAT AS pm10,
    so2::FLOAT AS so2,
    o3::FLOAT AS o3,
    co::FLOAT AS co,
    pm25::FLOAT AS pm25,

    -- Metadatos y calidad del aire
    calidad_am AS estado_calidad_aire,

    -- Ubicación geográfica
    direccion,
    tipozona AS tipo_zona,
    tipoemisio AS tipo_emision,

    -- Coordenadas geográficas (extraer del JSONB geo_point_2d)
    (geo_point_2d->>'lat')::FLOAT AS latitud,
    (geo_point_2d->>'lon')::FLOAT AS longitud,

    -- Timestamps (marcas de tiempo)
    fecha_carg AS fecha_hora_medicion,
    ingested_at AS fecha_ingesta,

    -- ID interno de la fila en la tabla raw
    id AS id_fila_raw,

    -- Otros campos útiles
    parametros AS parametros_medidos,
    mediciones AS mediciones_texto,
    fiwareid AS fiware_id

FROM {{ source('air_quality', 'valencia_air_real_hourly') }}

-- Filtrar solo registros con timestamp válido
WHERE fecha_carg IS NOT NULL
WITH raw_data AS (
    SELECT 
        station_id,
        data_raw,
        timestamp AS ingested_at
    -- Usamos la referencia a la tabla que creó tu app de Python
    FROM {{ source('air_quality', 'valencia_air') }}
)

SELECT
    -- Identificadores básicos
    station_id,
    jsonb_extract_path_text(data_raw, 'nombre')::TEXT AS station_name,
    
    -- Magnitudes (convertidas a FLOAT para poder hacer cálculos)
    jsonb_extract_path_text(data_raw, 'no2')::FLOAT AS no2,
    jsonb_extract_path_text(data_raw, 'pm10')::FLOAT AS pm10,
    jsonb_extract_path_text(data_raw, 'so2')::FLOAT AS so2,
    jsonb_extract_path_text(data_raw, 'o3')::FLOAT AS o3,
    jsonb_extract_path_text(data_raw, 'co')::FLOAT AS co,
    jsonb_extract_path_text(data_raw, 'pm25')::FLOAT AS pm25,

    -- Metadatos y calidad
    jsonb_extract_path_text(data_raw, 'calidad_am')::TEXT AS air_quality_status,
    
    -- Timestamps (Convertimos el texto de la API a formato fecha real)
    (jsonb_extract_path_text(data_raw, 'fecha_carg'))::TIMESTAMP WITH TIME ZONE AS measure_timestamp,
    ingested_at

FROM raw_data
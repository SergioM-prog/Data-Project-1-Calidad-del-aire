-- Este modelo junta las diferentes fuentes de staging en una sola estructura unificada
WITH valencia_data AS (
    SELECT
        measure_timestamp,
        station_id,
        station_name,
        -- Añadimos la dimensión de ciudad para distinguir el origen
        'Valencia' AS city,
        -- Traemos los contaminantes ya limpios y tipados
        no2,
        pm10,
        so2,
        o3,
        co,
        pm25,
        air_quality_status
    FROM {{ ref('stg_valencia_air') }}
),

-- Dejamos preparada la estructura de Madrid (aunque esté vacía por ahora)
madrid_placeholder AS (
    SELECT
        NULL::TIMESTAMP WITH TIME ZONE AS measure_timestamp,
        NULL::INTEGER AS station_id,
        NULL::TEXT AS station_name,
        'Madrid' AS city,
        NULL::FLOAT AS no2,
        NULL::FLOAT AS pm10,
        NULL::FLOAT AS so2,
        NULL::FLOAT AS o3,
        NULL::FLOAT AS co,
        NULL::FLOAT AS pm25,
        NULL::TEXT AS air_quality_status
    WHERE FALSE -- Esto asegura que esta parte no devuelva nada de momento
)

-- Unión de todas las fuentes
SELECT * FROM valencia_data
UNION ALL
SELECT * FROM madrid_placeholder
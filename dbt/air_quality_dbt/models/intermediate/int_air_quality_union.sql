-- Este modelo junta las diferentes fuentes de staging en una sola estructura unificada
WITH valencia_data AS (
    SELECT
        fecha_hora_medicion,
        id_estacion,
        nombre_estacion,
        -- Añadimos la dimensión de ciudad para distinguir el origen
        'Valencia' AS ciudad,
        -- Traemos los contaminantes ya limpios y tipados
        no2,
        pm10,
        so2,
        o3,
        co,
        pm25,
        estado_calidad_aire
    FROM {{ ref('stg_valencia_air') }}
),

-- Dejamos preparada la estructura de Madrid (aunque esté vacía por ahora)
madrid_placeholder AS (
    SELECT
        NULL::TIMESTAMP WITH TIME ZONE AS fecha_hora_medicion,
        NULL::INTEGER AS id_estacion,
        NULL::TEXT AS nombre_estacion,
        'Madrid' AS ciudad,
        NULL::FLOAT AS no2,
        NULL::FLOAT AS pm10,
        NULL::FLOAT AS so2,
        NULL::FLOAT AS o3,
        NULL::FLOAT AS co,
        NULL::FLOAT AS pm25,
        NULL::TEXT AS estado_calidad_aire
    WHERE FALSE -- Esto asegura que esta parte no devuelva nada de momento
)

-- Unión de todas las fuentes
SELECT * FROM valencia_data
UNION ALL
SELECT * FROM madrid_placeholder
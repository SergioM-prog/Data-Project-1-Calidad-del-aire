-- Agrupamos por día para ver tendencias históricas
SELECT
    measure_timestamp::DATE AS measure_date,
    city,
    station_id,
    station_name,
    ROUND(AVG(no2)::numeric, 2) AS daily_avg_no2,
    ROUND(AVG(pm10)::numeric, 2) AS daily_avg_pm10,
    ROUND(AVG(pm25)::numeric, 2) AS daily_avg_pm25,
    -- Calculamos el valor máximo del día para alertas
    MAX(no2) AS max_no2_peak,
    MAX(pm10) AS max_pm10_peak
FROM {{ ref('int_air_quality_union') }}
WHERE measure_timestamp IS NOT NULL
GROUP BY 1, 2, 3, 4
ORDER BY 1 DESC, 2
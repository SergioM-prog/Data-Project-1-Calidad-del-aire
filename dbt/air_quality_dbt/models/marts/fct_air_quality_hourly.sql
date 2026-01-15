-- Agrupamos por hora, ciudad y estación para ver la evolución intradía
SELECT
    date_trunc('hour', measure_timestamp) AS measure_hour,
    city,
    station_id,
    station_name,
    ROUND(AVG(no2)::numeric, 2) AS avg_no2,
    ROUND(AVG(pm10)::numeric, 2) AS avg_pm10,
    ROUND(AVG(pm25)::numeric, 2) AS avg_pm25,
    ROUND(AVG(so2)::numeric, 2) AS avg_so2,
    ROUND(AVG(o3)::numeric, 2) AS avg_o3,
    ROUND(AVG(co)::numeric, 2) AS avg_co,
    COUNT(*) AS records_count -- Útil para saber si hay datos faltantes en esa hora
FROM {{ ref('int_air_quality_union') }}
WHERE measure_timestamp IS NOT NULL -- Filtramos los placeholders de Madrid
GROUP BY 1, 2, 3, 4
ORDER BY 1 DESC, 2
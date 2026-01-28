with source as (

    select * from {{ ref('int_air_quality_union_hourly') }}
    where fecha_hora_medicion is not null

)

select
    id_estacion,
    nombre_estacion,
    ciudad,
    extract(hour from fecha_hora_medicion)::int as hora,
    round(percentile_cont(0.75) within group (order by no2)::numeric, 2)::float as p75_no2,
    round(percentile_cont(0.75) within group (order by pm10)::numeric, 2)::float as p75_pm10,
    round(percentile_cont(0.75) within group (order by pm25)::numeric, 2)::float as p75_pm25,
    round(percentile_cont(0.75) within group (order by so2)::numeric, 2)::float as p75_so2,
    round(percentile_cont(0.75) within group (order by o3)::numeric, 2)::float as p75_o3,
    round(percentile_cont(0.75) within group (order by co)::numeric, 2)::float as p75_co,
    count(*) as total_mediciones
from source
group by id_estacion, nombre_estacion, ciudad, hora
order by id_estacion, hora

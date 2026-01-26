with source as (

    select * from {{ ref('int_air_quality_union_hourly') }}
    where fecha_hora_medicion is not null

)

select
    id_estacion,
    nombre_estacion,
    ciudad,
    extract(hour from fecha_hora_medicion)::int as hora,
    round(avg(no2)::numeric, 2)::float as promedio_no2,
    round(avg(pm10)::numeric, 2)::float as promedio_pm10,
    round(avg(pm25)::numeric, 2)::float as promedio_pm25,
    round(avg(so2)::numeric, 2)::float as promedio_so2,
    round(avg(o3)::numeric, 2)::float as promedio_o3,
    round(avg(co)::numeric, 2)::float as promedio_co,
    count(*) as total_mediciones
from source
group by id_estacion, nombre_estacion, ciudad, hora
order by id_estacion, hora

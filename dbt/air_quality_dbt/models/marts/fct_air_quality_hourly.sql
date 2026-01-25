with

source as (

    select * from {{ ref('int_air_quality_union') }}
    where fecha_hora_medicion is not null

),

hourly_aggregates as (

    select
        date_trunc('hour', fecha_hora_medicion) as fecha_hora,
        ciudad,
        id_estacion,
        nombre_estacion,
        round(avg(no2)::numeric, 2)::float as promedio_no2,
        round(avg(pm10)::numeric, 2)::float as promedio_pm10,
        round(avg(pm25)::numeric, 2)::float as promedio_pm25,
        round(avg(so2)::numeric, 2)::float as promedio_so2,
        round(avg(o3)::numeric, 2)::float as promedio_ozono,
        round(avg(co)::numeric, 2)::float as promedio_co,
        count(*) as total_mediciones_hora
    from source
    group by 1, 2, 3, 4

)

select * from hourly_aggregates
order by fecha_hora desc, ciudad

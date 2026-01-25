with

source as (

    select * from {{ ref('int_air_quality_union') }}
    where fecha_hora_medicion is not null

),

daily_aggregates as (

    select
        fecha_hora_medicion::date as fecha_medicion,
        ciudad,
        id_estacion,
        nombre_estacion,
        round(avg(no2)::numeric, 2)::float as promedio_diario_no2,
        round(avg(pm10)::numeric, 2)::float as promedio_diario_pm10,
        round(avg(pm25)::numeric, 2)::float as promedio_diario_pm25,
        round(max(no2)::numeric, 2)::float as pico_no2,
        round(max(pm10)::numeric, 2)::float as pico_pm10,
        count(*) as total_mediciones_dia
    from source
    group by 1, 2, 3, 4

)

select * from daily_aggregates
order by fecha_medicion desc, ciudad

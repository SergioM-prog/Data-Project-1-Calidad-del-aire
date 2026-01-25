{{ config(materialized='table') }}

with

source as (

    select * from {{ ref('stg_valencia_air') }}

),

weekly_aggregates as (

    select
        date_trunc('week', fecha_hora_medicion) as inicio_semana,
        date_trunc('week', fecha_hora_medicion) + interval '6 days' as fin_semana,
        extract(week from fecha_hora_medicion) as numero_semana,
        extract(year from fecha_hora_medicion) as anio,
        id_estacion,
        nombre_estacion,
        round(avg(no2)::numeric, 2)::float as promedio_semanal_no2,
        round(avg(pm10)::numeric, 2)::float as promedio_semanal_pm10,
        round(avg(pm25)::numeric, 2)::float as promedio_semanal_pm25,
        round(avg(so2)::numeric, 2)::float as promedio_semanal_so2,
        round(avg(o3)::numeric, 2)::float as promedio_semanal_ozono,
        round(avg(co)::numeric, 2)::float as promedio_semanal_co,
        round(max(pm25)::numeric, 2)::float as maximo_pm25_semana,
        round(max(pm10)::numeric, 2)::float as maximo_pm10_semana,
        round(max(no2)::numeric, 2)::float as maximo_no2_semana,
        round(min(pm25)::numeric, 2)::float as minimo_pm25_semana,
        round(min(pm10)::numeric, 2)::float as minimo_pm10_semana,
        round(min(no2)::numeric, 2)::float as minimo_no2_semana,
        count(*) as total_mediciones_semana,
        count(distinct date(fecha_hora_medicion)) as dias_con_datos,
        case
            when avg(pm25) is null then 'Sin Datos'
            when avg(pm25) <= 10 then 'Semana Buena'
            when avg(pm25) <= 15 then 'Semana Moderada'
            when avg(pm25) <= 25 then 'Semana Pobre'
            else 'Semana Muy Contaminada'
        end as clasificacion_semana,
        'Valencia' as ciudad
    from source
    group by 1, 2, 3, 4, 5, 6

)

select * from weekly_aggregates
order by inicio_semana desc, nombre_estacion

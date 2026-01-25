{{ config(materialized='table') }}

with

source as (

    select * from {{ ref('stg_valencia_air') }}
    where fecha_hora_medicion is not null

),

detailed_measurements as (

    select
        fecha_hora_medicion,
        date_trunc('hour', fecha_hora_medicion) as hora_agrupada,
        date(fecha_hora_medicion) as fecha,
        extract(hour from fecha_hora_medicion) as hora_del_dia,
        extract(dow from fecha_hora_medicion) as dia_semana,
        id_estacion,
        nombre_estacion,
        'Valencia' as ciudad,
        no2 as dioxido_nitrogeno,
        pm10 as particulas_gruesas,
        pm25 as particulas_finas,
        so2 as dioxido_azufre,
        o3 as ozono,
        co as monoxido_carbono,
        estado_calidad_aire,
        case
            when pm25 is null then 'Sin Datos'
            when pm25 <= 5 then 'Excelente'
            when pm25 <= 10 then 'Buena'
            when pm25 <= 15 then 'Moderada'
            when pm25 <= 25 then 'Pobre'
            when pm25 <= 35 then 'Muy Pobre'
            else 'Peligrosa'
        end as clasificacion_pm25,
        case
            when no2 is null then 'Sin Datos'
            when no2 <= 10 then 'Excelente'
            when no2 <= 25 then 'Buena'
            when no2 <= 40 then 'Moderada'
            when no2 <= 50 then 'Pobre'
            else 'Peligrosa'
        end as clasificacion_no2
    from source

)

select * from detailed_measurements
order by fecha_hora_medicion desc

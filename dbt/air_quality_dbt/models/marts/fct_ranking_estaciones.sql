with

source as (

    select * from {{ ref('stg_valencia_air') }}
    where fecha_hora_medicion >= current_date - interval '30 days'

),

estadisticas_estacion as (

    select
        id_estacion,
        nombre_estacion,
        'Valencia' as ciudad,
        round(avg(pm25)::numeric, 2)::float as promedio_pm25,
        round(avg(pm10)::numeric, 2)::float as promedio_pm10,
        round(avg(no2)::numeric, 2)::float as promedio_no2,
        round(avg(so2)::numeric, 2)::float as promedio_so2,
        round(avg(o3)::numeric, 2)::float as promedio_ozono,
        round(avg(co)::numeric, 2)::float as promedio_co,
        round(max(pm25)::numeric, 2)::float as maximo_pm25,
        round(max(pm10)::numeric, 2)::float as maximo_pm10,
        round(max(no2)::numeric, 2)::float as maximo_no2,
        count(*) as total_mediciones
    from source
    group by id_estacion, nombre_estacion, ciudad

),

ranked as (

    select
        *,
        rank() over (order by promedio_pm25 desc) as ranking_pm25,
        rank() over (order by promedio_pm10 desc) as ranking_pm10,
        rank() over (order by promedio_no2 desc) as ranking_no2,
        rank() over (order by promedio_so2 desc) as ranking_so2,
        rank() over (order by promedio_ozono desc) as ranking_ozono,
        round((
            rank() over (order by promedio_pm25 desc) +
            rank() over (order by promedio_pm10 desc) +
            rank() over (order by promedio_no2 desc)
        )::numeric / 3.0, 1)::float as ranking_general,
        case
            when round((
                rank() over (order by promedio_pm25 desc) +
                rank() over (order by promedio_pm10 desc) +
                rank() over (order by promedio_no2 desc)
            )::numeric / 3.0, 1) <= 3 then 'Zona Muy Contaminada'
            when round((
                rank() over (order by promedio_pm25 desc) +
                rank() over (order by promedio_pm10 desc) +
                rank() over (order by promedio_no2 desc)
            )::numeric / 3.0, 1) <= 7 then 'Zona Contaminada'
            when round((
                rank() over (order by promedio_pm25 desc) +
                rank() over (order by promedio_pm10 desc) +
                rank() over (order by promedio_no2 desc)
            )::numeric / 3.0, 1) <= 12 then 'Zona Moderada'
            else 'Zona Limpia'
        end as clasificacion_zona
    from estadisticas_estacion

)

select * from ranked
order by promedio_pm25 desc

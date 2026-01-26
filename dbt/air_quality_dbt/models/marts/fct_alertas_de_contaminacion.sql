with

severidad_config as (

    select 1 as nivel, 'LEVE' as descripcion, 'Precaución para personas sensibles' as recomendacion
    union all select 2, 'MODERADO', 'Reducir actividad física intensa'
    union all select 3, 'GRAVE', 'Grupos sensibles evitar actividad exterior'
    union all select 4, 'CRÍTICO', 'Evitar salir'

),

alertas_base as (

    select
        fecha_hora_medicion as fecha_hora_alerta,
        date(fecha_hora_medicion) as fecha,
        extract(hour from fecha_hora_medicion) as hora,
        extract(dow from fecha_hora_medicion) as dia_semana,
        case extract(dow from fecha_hora_medicion)
            when 0 then 'Domingo'
            when 1 then 'Lunes'
            when 2 then 'Martes'
            when 3 then 'Miércoles'
            when 4 then 'Jueves'
            when 5 then 'Viernes'
            when 6 then 'Sábado'
        end as nombre_dia,
        id_estacion,
        nombre_estacion,
        'Valencia' as ciudad,
        round(coalesce(pm25, 0)::numeric, 2)::float as valor_pm25,
        round(coalesce(pm10, 0)::numeric, 2)::float as valor_pm10,
        round(coalesce(no2, 0)::numeric, 2)::float as valor_no2,
        round(coalesce(so2, 0)::numeric, 2)::float as valor_so2,
        round(coalesce(o3, 0)::numeric, 2)::float as valor_o3,
        round(coalesce(co, 0)::numeric, 2)::float as valor_co,
        (coalesce(pm25, 0) > 15) as tiene_alerta_pm25,
        (coalesce(pm10, 0) > 45) as tiene_alerta_pm10,
        (coalesce(no2, 0) > 25) as tiene_alerta_no2,
        (coalesce(so2, 0) > 40) as tiene_alerta_so2,
        (coalesce(o3, 0) > 100) as tiene_alerta_o3,
        round(((coalesce(pm25, 0) / 15.0) - 1.0)::numeric * 100, 1)::float as exceso_pm25_porcentaje,
        round(((coalesce(pm10, 0) / 45.0) - 1.0)::numeric * 100, 1)::float as exceso_pm10_porcentaje,
        round(((coalesce(no2, 0) / 25.0) - 1.0)::numeric * 100, 1)::float as exceso_no2_porcentaje,
        round(((coalesce(so2, 0) / 40.0) - 1.0)::numeric * 100, 1)::float as exceso_so2_porcentaje,
        round(((coalesce(o3, 0) / 100.0) - 1.0)::numeric * 100, 1)::float as exceso_o3_porcentaje,
        case
            when pm25 > 50 or pm10 > 150 or no2 > 75 or so2 > 150 or o3 > 240 then 4
            when pm25 > 35 or pm10 > 100 or no2 > 50 or so2 > 100 or o3 > 180 then 3
            when pm25 > 25 or pm10 > 70 or no2 > 40 or so2 > 60 or o3 > 140 then 2
            else 1
        end as nivel_severidad,
        case
            when pm25 / 15.0 = greatest(
                pm25 / 15.0,
                pm10 / 45.0,
                no2 / 25.0,
                coalesce(so2 / 40.0, 0),
                coalesce(o3 / 100.0, 0)
            ) then 'PM2.5'
            when pm10 / 45.0 = greatest(
                pm25 / 15.0,
                pm10 / 45.0,
                no2 / 25.0,
                coalesce(so2 / 40.0, 0),
                coalesce(o3 / 100.0, 0)
            ) then 'PM10'
            when no2 / 25.0 = greatest(
                pm25 / 15.0,
                pm10 / 45.0,
                no2 / 25.0,
                coalesce(so2 / 40.0, 0),
                coalesce(o3 / 100.0, 0)
            ) then 'NO2'
            when so2 > 40 and so2 / 40.0 = greatest(
                pm25 / 15.0,
                pm10 / 45.0,
                no2 / 25.0,
                so2 / 40.0,
                coalesce(o3 / 100.0, 0)
            ) then 'SO2'
            when o3 > 100 and o3 / 100.0 = greatest(
                pm25 / 15.0,
                pm10 / 45.0,
                no2 / 25.0,
                coalesce(so2 / 40.0, 0),
                o3 / 100.0
            ) then 'O3'
            else 'MÚLTIPLE'
        end as contaminante_principal
    from {{ ref('stg_valencia_air') }}
    where
        pm25 > 15
        or pm10 > 45
        or no2 > 25
        or so2 > 40
        or o3 > 100

)

select
    a.*,
    s.descripcion as descripcion_severidad,
    s.recomendacion
from alertas_base a
left join severidad_config s on a.nivel_severidad = s.nivel
order by a.fecha_hora_alerta desc, a.nivel_severidad desc

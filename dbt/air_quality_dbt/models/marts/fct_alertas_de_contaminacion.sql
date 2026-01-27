with

mediciones as (
    select
        fecha_hora_medicion,
        id_estacion,
        nombre_estacion,
        extract(hour from fecha_hora_medicion)::int as hora,
        no2, pm10, pm25, so2, o3, co
    from {{ ref('stg_valencia_air') }}
    where fecha_hora_medicion is not null
),

limites as (
    select id_estacion, hora, promedio_no2, promedio_pm10, promedio_pm25, promedio_so2, promedio_o3, promedio_co
    from {{ ref('fct_limites_de_contaminacion') }}
)

select
    m.fecha_hora_medicion as fecha_hora_alerta,
    m.id_estacion,
    m.nombre_estacion,
    'Valencia' as ciudad,
    m.hora,
    m.no2 as valor_no2,
    m.pm10 as valor_pm10,
    m.pm25 as valor_pm25,
    m.so2 as valor_so2,
    m.o3 as valor_o3,
    m.co as valor_co,
    l.promedio_no2 as limite_no2,
    l.promedio_pm10 as limite_pm10,
    l.promedio_pm25 as limite_pm25,
    l.promedio_so2 as limite_so2,
    l.promedio_o3 as limite_o3,
    l.promedio_co as limite_co,
    (m.no2 > l.promedio_no2) as alerta_no2,
    (m.pm10 > l.promedio_pm10) as alerta_pm10,
    (m.pm25 > l.promedio_pm25) as alerta_pm25,
    (m.so2 > l.promedio_so2) as alerta_so2,
    (m.o3 > l.promedio_o3) as alerta_o3,
    (m.co > l.promedio_co) as alerta_co,
    false as alerta_informada
from mediciones m
inner join limites l on m.id_estacion = l.id_estacion and m.hora = l.hora
where
    m.no2 > l.promedio_no2
    or m.pm10 > l.promedio_pm10
    or m.pm25 > l.promedio_pm25
    or m.so2 > l.promedio_so2
    or m.o3 > l.promedio_o3
    or m.co > l.promedio_co
order by fecha_hora_alerta desc

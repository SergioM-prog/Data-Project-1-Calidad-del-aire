with

source as (

    select * from {{ ref('int_air_quality_union_hourly') }}
    where fecha_hora_medicion is not null

),

estaciones_agregadas as (

    select
        id_estacion,
        nombre_estacion,
        ciudad,
        min(fecha_hora_medicion) as primera_medicion,
        max(fecha_hora_medicion) as ultima_medicion,
        count(*) as total_mediciones,
        date_part('day', max(fecha_hora_medicion) - min(fecha_hora_medicion)) as dias_activa
    from source
    group by id_estacion, nombre_estacion, ciudad

)

select * from estaciones_agregadas
order by total_mediciones desc

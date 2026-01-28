with

-- 1: Obtener datos horarios de intermediate
source_hourly as (

    select * from {{ ref('int_air_quality_union_hourly') }}
    where fecha_hora_medicion is not null

),

-- 2: Agregar datos horarios a diarios
-- Calculamos promedios, picos y conteo de mediciones por día
daily_from_intermediate as (

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
        count(*) as total_mediciones_dia,
        'intermediate' as origen,
        2 as prioridad
    from source_hourly
    group by 1, 2, 3, 4

),

-- 3: Datos históricos reales diarios de Valencia (ya vienen agregados)

daily_from_historical as (

    select
        fecha_hora_medicion::date as fecha_medicion,
        'Valencia' as ciudad,
        id_estacion,
        nombre_estacion,
        round(no2::numeric, 2)::float as promedio_diario_no2,
        round(pm10::numeric, 2)::float as promedio_diario_pm10,
        round(pm25::numeric, 2)::float as promedio_diario_pm25,
        round(no2::numeric, 2)::float as pico_no2,
        round(pm10::numeric, 2)::float as pico_pm10,
        1 as total_mediciones_dia,
        'historical_real' as origen,
        1 as prioridad
    from {{ ref('stg_valencia_air_historical_real_daily') }}

),

-- 4: Unir ambas fuentes (ambas ya son diarias)

combined_data as (

    select * from daily_from_intermediate
    union all
    select * from daily_from_historical

),

-- 5: Deduplicar priorizando datos históricos reales (prioridad 1)
-- Si hay duplicados por id_estacion + fecha_medicion, prevalece historical_real

deduplicated as (

    select
        *,
        row_number() over (
            partition by id_estacion, fecha_medicion
            order by prioridad asc
        ) as fila_numero
    from combined_data

)

select
    fecha_medicion,
    ciudad,
    id_estacion,
    nombre_estacion,
    promedio_diario_no2,
    promedio_diario_pm10,
    promedio_diario_pm25,
    pico_no2,
    pico_pm10,
    total_mediciones_dia,
    origen
from deduplicated
where fila_numero = 1
order by fecha_medicion desc, ciudad

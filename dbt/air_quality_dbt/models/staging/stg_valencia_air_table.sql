-- STAGING TABLE: Versión materializada como tabla del staging view
--
-- ¿Qué hace?
-- Crea una tabla física a partir del view stg_valencia_air
-- para consultas más rápidas cuando no necesitas datos en tiempo real
--
-- Usa {{ ref() }} para leer del modelo view

{{ config(materialized='table') }}

SELECT * FROM {{ ref('stg_valencia_air') }}   -- Consultas rápidas, lee del view  -- seguir analizando 

-- https://docs.getdbt.com/docs/build/materializations

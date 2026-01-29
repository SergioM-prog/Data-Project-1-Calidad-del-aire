from fastapi import FastAPI, HTTPException, Depends, Security, Query
from fastapi.security import APIKeyHeader
from config import engine
import pandas as pd
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from sqlalchemy import types, text
from contextlib import asynccontextmanager
from database import init_db, load_historical_real_data, load_historical_simulated_data
from sqlalchemy.dialects.postgresql import insert
import math


# ----------------------------------

# Clase principal de la medición
class AirQualityInbound(BaseModel):
    # Identificadores (Obligatorios)
    objectid: int
    fiwareid: str
    nombre: str
    direccion: str
    
    # Contexto de la zona
    tipozona: str
    tipoemisio: str
    calidad_am: str
    fecha_carg: str
    
    # Parámetros descriptivos (Pueden ser nulos en el JSON)
    parametros: Optional[str] = None
    mediciones: Optional[str] = None

    # Mediciones de Contaminantes (Opcionales para evitar errores si falta alguno)
    so2: Optional[float] = None
    no2: Optional[float] = None
    o3: Optional[float] = None
    co: Optional[float] = None
    pm10: Optional[float] = None
    pm25: Optional[float] = None

    # Geografía: Definidos como diccionarios genéricos por ahora
    # Solo validamos que sea un diccionario, no miramos qué hay dentro.

    geo_shape: Dict[str, Any]   # Le decimos a pylance que la clave del diccionario debe ser string pero el valor asociado a la clave puede ser cualquiera
    geo_point_2d: Dict[str, Any]

    # CONFIGURACIÓN DE SEGURIDAD
    # 'forbid' asegura que no aceptamos ningún campo nuevo que no esté en esta lista

    model_config = ConfigDict(extra='forbid')

# ----------------------------------

@asynccontextmanager    # El decorador es un envoltorio funcional. Le dice a python que la función es un Gestor de Contexto (Context Manager) y tiene dos tiempos, una al arrancar (Antes del yield) y otra al apagar la api (Despues del yield)
async def lifespan(app: FastAPI):

    # --- CÓDIGO AL ARRANCAR EL CONTENEDOR ---

    try:
        init_db()
        # Cargar datos históricos (solo se ejecuta si la tabla está vacía)
        load_historical_real_data("/app/historical/real", "valencia_air_historical_real_daily") # Cargamos los datos históricos reales diarios sacados de la api
        
        load_historical_simulated_data("/app/historical/simulated", "valencia_air_historical_simulated_hourly") # Cargamos los datos históricos simulados horarios sacados de la api
        
    except Exception as e:
        print(f"❌ Error inicializando la BD: {e}")
    yield   #Pausa la ejecución de la función para seguir con la aplicación.
            #Se pueden configurar acciones a realizar al apagar la api

# Inicialización de la API
app = FastAPI(
    lifespan=lifespan,
    title="Air Quality Barrier API",
    description="API de aislamiento para proteger el acceso a air_quality_db",
    version="1.0.0"
)

# ----------------------------------

# --- AUTENTICACIÓN M2M ---

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Dependencia de FastAPI para validar API keys.
    Verifica que la key exista en security.api_key_clients y esté activa.
    Retorna el nombre del servicio autenticado.
    """
    if not api_key:
        raise HTTPException(status_code=401, detail="API Key requerida. Incluye el header 'X-API-Key'.")

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT service_name FROM security.api_key_clients
            WHERE api_key = :api_key AND is_active = TRUE
        """), {"api_key": api_key})
        client = result.fetchone()

    if not client:
        raise HTTPException(status_code=403, detail="API Key inválida o servicio desactivado.")

    return client.service_name

# ----------------------------------

# Definimos un método de inserción personalizado de Pandas para insertar datos en la BD
# evitando que se generen registros duplicados.
# La función .to_sql le inyecta los parámetros al llamar a la función

def insert_with_ignore_duplicates(table, conn, keys, data_iter):

    data = [dict(zip(keys, row)) for row in data_iter]
    if data:
        stmt = insert(table.table).values(data)
        stmt = stmt.on_conflict_do_nothing(index_elements=['objectid', 'fecha_carg'])
        conn.execute(stmt)


# --- ENDPOINTS ---

@app.get("/health")
async def health_check():
    """
    Endpoint de salud para verificar que el backend está operativo.
    Verifica conexión a la base de datos.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {e}")


# --- ENDPOINTS INGESTA ---

@app.post("/api/ingest", status_code=201)
async def ingest_air_data(data: list[AirQualityInbound], service: str = Depends(verify_api_key)):
    try:
        # 1. Convertimos la lista de modelos Pydantic a una lista de diccionarios Python
        # model_dump() es el estándar moderno de Pydantic v2

        payload = [item.model_dump() for item in data]

        # 2. Creamos el DataFrame. Al ser las llaves del JSON iguales a las
        # columnas de la tabla, el mapeo es automático.

        df = pd.DataFrame(payload)

        # 3. Inserción en la tabla raw.valencia_air_real_hourly
        # Usamos method personalizado para ignorar duplicados automáticamente
        # Especificamos dtype para asegurar que los diccionarios se traten como JSONB

        df.to_sql(
            'valencia_air_real_hourly',
            engine,
            schema='raw',
            if_exists='append',
            index=False,
            method=insert_with_ignore_duplicates,
            dtype={
                'geo_shape': types.JSON,
                'geo_point_2d': types.JSON,
                'fecha_carg': types.DateTime(timezone=True)
            }
        )

        return {
            "status": "success",
            "message": f"Se procesaron {len(df)} registros (duplicados ignorados automáticamente)."
        }

    except Exception as e:
        print(f"Error crítico en la ingesta: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error al procesar la inserción en las columnas de la base de datos"
        )



# --- ENDPOINTS DE ALERTAS TELEGRAM ---

@app.get("/api/alertas")
async def get_alertas_pendientes(service: str = Depends(verify_api_key)):
    """Devuelve alertas de contaminación pendientes de enviar a Telegram."""
    query = """
        SELECT a.*
        FROM marts.fct_alertas_actuales_contaminacion a
        WHERE NOT EXISTS (
            SELECT 1 FROM alerts.alertas_enviadas_telegram e
            WHERE e.id_estacion = a.id_estacion
            AND e.fecha_hora_alerta = a.fecha_hora_alerta
        )
        ORDER BY a.fecha_hora_alerta DESC
    """
    with engine.connect() as conn:
        result = conn.execute(text(query))
        alertas = [dict(row._mapping) for row in result]
    return {"alertas": alertas, "total": len(alertas)}


@app.post("/api/alertas/registrar-envio")
async def registrar_alerta_enviada(alertas: list[dict], service: str = Depends(verify_api_key)):

    """Registra en el histórico las alertas enviadas a Telegram."""
    with engine.connect() as conn:
        for alerta in alertas:
            conn.execute(text("""
                INSERT INTO alerts.alertas_enviadas_telegram
                (id_estacion, fecha_hora_alerta, nombre_estacion, ciudad, parametro, valor, limite)
                VALUES (:id_estacion, :fecha_hora_alerta, :nombre_estacion, :ciudad, :parametro, :valor, :limite)
                ON CONFLICT (id_estacion, fecha_hora_alerta, parametro) DO NOTHING
            """), alerta)
        conn.commit()
    return {"status": "success", "alertas_registradas": len(alertas)}

# --- ENDPOINTS PLOTLI ---

@app.get("/api/hourly-metrics")
def get_hourly_metrics(limit: int = Query(100, ge=1, le=5000), service: str = Depends(verify_api_key)):
    """
    Devuelve las últimas métricas horarias (JSON seguro: sin NaN/Inf).
    """
    try:
        query = f"""
            SELECT *
            FROM marts.fct_air_quality_hourly
            ORDER BY fecha_hora DESC
            LIMIT {limit}
        """
        df = pd.read_sql(query, engine)

        # ✅ Convertir NaN/Inf a None para que JSON no rompa
        records = df.to_dict(orient="records")
        for row in records:
            for k, v in row.items():
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    row[k] = None

        return records

    except Exception as e:
        print(f"Error en API: {e}")
        raise HTTPException(status_code=500, detail="Error interno al leer base de datos")


#Podio
@app.get("/api/zonas-verdes")
def get_zonas_verdes(limit: int = Query(3, ge=1, le=10), service: str = Depends(verify_api_key)):

    """
    Devuelve las estaciones con mejor calidad del aire (menor contaminación).
    Solo incluye estaciones donde NINGÚN contaminante supere su umbral.
    Umbrales: NO2=25, PM2.5=15, PM10=45, O3=100, SO2=40 µg/m³
    """
    try:
        query = """
            WITH ultimas_mediciones AS (
                SELECT DISTINCT ON (id_estacion)
                    id_estacion,
                    nombre_estacion,
                    promedio_no2,
                    promedio_pm25,
                    promedio_pm10,
                    promedio_ozono,
                    promedio_so2,
                    fecha_hora
                FROM marts.fct_air_quality_hourly
                ORDER BY id_estacion, fecha_hora DESC
            ),
            sin_alertas AS (
                SELECT
                    id_estacion,
                    nombre_estacion,
                    fecha_hora,
                    promedio_no2,
                    promedio_pm25,
                    promedio_pm10,
                    promedio_ozono,
                    promedio_so2,
                    COALESCE(promedio_no2, 0) + COALESCE(promedio_pm25, 0) + COALESCE(promedio_pm10, 0) +
                    COALESCE(promedio_ozono, 0) + COALESCE(promedio_so2, 0) AS indice_contaminacion
                FROM ultimas_mediciones
                WHERE nombre_estacion IS NOT NULL
                  AND (promedio_no2 IS NULL OR promedio_no2 <= 25)
                  AND (promedio_pm25 IS NULL OR promedio_pm25 <= 15)
                  AND (promedio_pm10 IS NULL OR promedio_pm10 <= 45)
                  AND (promedio_ozono IS NULL OR promedio_ozono <= 100)
                  AND (promedio_so2 IS NULL OR promedio_so2 <= 40)
            )
            SELECT
                id_estacion,
                nombre_estacion,
                promedio_no2,
                promedio_pm25,
                promedio_pm10,
                promedio_ozono,
                promedio_so2,
                indice_contaminacion,
                ROW_NUMBER() OVER (ORDER BY indice_contaminacion ASC) as ranking_pos
            FROM sin_alertas
            ORDER BY indice_contaminacion ASC
            LIMIT %(limit)s
        """
        df = pd.read_sql(query, engine, params={"limit": limit})

        if df.empty:
            return []

        records = df.to_dict(orient="records")
        for row in records:
            for k, v in row.items():
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    row[k] = None

        return records

    except Exception as e:
        print(f"Error en zonas-verdes: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener zonas verdes")




@app.get("/api/station/latest-hourly")
def get_station_latest_hourly(station_id: int = Query(..., ge=1), service: str = Depends(verify_api_key)):
    """
    Devuelve la fila más reciente (última hora) de marts.fct_air_quality_hourly para una estación.
    """
    try:
        query = """
            SELECT *
            FROM marts.fct_air_quality_hourly
            WHERE id_estacion = %(station_id)s
            ORDER BY fecha_hora DESC
            LIMIT 1
        """
        df = pd.read_sql(query, engine, params={"station_id": station_id})

        if df.empty:
            return {}

        record = df.to_dict(orient="records")[0]

        # JSON seguro
        for k, v in list(record.items()):
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                record[k] = None

        return record

    except Exception as e:
        print(f"Error latest-hourly: {e}")
        raise HTTPException(status_code=500, detail="Error interno al leer base de datos")
    
@app.get("/api/alerts/now")
def get_alert_now(station_id: int = Query(..., ge=1),service: str = Depends(verify_api_key)):
    """
    Devuelve el semáforo + recomendación actual para una estación,
    leyendo desde marts.fct_alertas_actuales_contaminacion.
    """
    try:
        q = text("""
            WITH alertas_con_severidad AS (
                SELECT
                    fecha_hora_alerta,
                    id_estacion,
                    nombre_estacion,
                    ciudad,
                    CASE
                        WHEN alerta_no2 THEN 'NO2'
                        WHEN alerta_pm25 THEN 'PM2.5'
                        WHEN alerta_pm10 THEN 'PM10'
                        WHEN alerta_so2 THEN 'SO2'
                        WHEN alerta_o3 THEN 'O3'
                        WHEN alerta_co THEN 'CO'
                        ELSE 'Desconocido'
                    END as contaminante_principal,
                    CASE
                        WHEN (alerta_no2::int + alerta_pm25::int + alerta_pm10::int +
                              alerta_so2::int + alerta_o3::int + alerta_co::int) >= 3 THEN 3
                        WHEN (alerta_no2::int + alerta_pm25::int + alerta_pm10::int +
                              alerta_so2::int + alerta_o3::int + alerta_co::int) >= 2 THEN 2
                        ELSE 1
                    END as nivel_severidad,
                    CASE
                        WHEN (alerta_no2::int + alerta_pm25::int + alerta_pm10::int +
                              alerta_so2::int + alerta_o3::int + alerta_co::int) >= 3
                        THEN 'Alerta Grave - Múltiples contaminantes exceden límites'
                        WHEN (alerta_no2::int + alerta_pm25::int + alerta_pm10::int +
                              alerta_so2::int + alerta_o3::int + alerta_co::int) >= 2
                        THEN 'Alerta Moderada - Varios contaminantes elevados'
                        ELSE 'Alerta Leve - Contaminante elevado'
                    END as descripcion_severidad,
                    CASE
                        WHEN (alerta_no2::int + alerta_pm25::int + alerta_pm10::int +
                              alerta_so2::int + alerta_o3::int + alerta_co::int) >= 3
                        THEN 'Evite actividades al aire libre. Permanezca en interiores con ventanas cerradas.'
                        WHEN (alerta_no2::int + alerta_pm25::int + alerta_pm10::int +
                              alerta_so2::int + alerta_o3::int + alerta_co::int) >= 2
                        THEN 'Reduzca actividades físicas intensas al aire libre. Use mascarilla si es necesario.'
                        ELSE 'Limite actividades físicas prolongadas al aire libre.'
                    END as recomendacion
                FROM marts.fct_alertas_actuales_contaminacion
                WHERE id_estacion = :station_id
            )
            SELECT
                fecha_hora_alerta,
                id_estacion,
                nombre_estacion,
                nivel_severidad,
                contaminante_principal,
                descripcion_severidad,
                recomendacion
            FROM alertas_con_severidad
            ORDER BY fecha_hora_alerta DESC
            LIMIT 1;
        """)

        with engine.connect() as conn:
            row = conn.execute(q, {"station_id": station_id}).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail="No hay alerta disponible para esa estación.")

        # devolvemos dict JSON-friendly
        return dict(row)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error en API alerts/now: {e}")
        raise HTTPException(status_code=500, detail="Error interno al leer alerts/now")

@app.get("/air_quality/history")
def air_quality_history(station_id: int, window: str = "now", service: str = Depends(verify_api_key)):
    rows = []

    # --- tu lógica actual de histórico ---
    rows.append({
        "timestamp": "2026-01-26T10:00:00",
        "nivel_severidad": 3,
    })

    # Obtener coordenadas desde la tabla marts.fct_dim_estaciones
    try:
        query = """
            SELECT latitud, longitud
            FROM marts.fct_dim_estaciones
            WHERE id_estacion = %(station_id)s
            LIMIT 1
        """
        df = pd.read_sql(query, engine, params={"station_id": station_id})

        if not df.empty:
            lat = df.iloc[0]['latitud']
            lon = df.iloc[0]['longitud']

            for r in rows:
                r["lat"] = lat
                r["lon"] = lon
    except Exception as e:
        print(f"Error al obtener coordenadas: {e}")

    return rows

@app.get("/api/stations")
def get_stations(service: str = Depends(verify_api_key)):
    """
    Devuelve la lista de estaciones únicas con su ID y nombre.
    """
    try:
        query = """
            SELECT DISTINCT id_estacion, nombre_estacion
            FROM marts.fct_air_quality_hourly
            WHERE nombre_estacion IS NOT NULL
            ORDER BY nombre_estacion
        """
        df = pd.read_sql(query, engine)
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"Error en stations: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener estaciones")


@app.get("/api/limites/{station_id}")
def get_limites_estacion(station_id: int, service: str = Depends(verify_api_key)):
    """
    Devuelve los límites dinámicos (P75) para una estación específica.
    Calcula el promedio de los límites de todas las horas.
    """
    try:
        query = """
            SELECT
                ROUND(AVG(p75_no2)::numeric, 2)::float as limite_no2,
                ROUND(AVG(p75_pm10)::numeric, 2)::float as limite_pm10,
                ROUND(AVG(p75_pm25)::numeric, 2)::float as limite_pm25,
                ROUND(AVG(p75_so2)::numeric, 2)::float as limite_so2,
                ROUND(AVG(p75_o3)::numeric, 2)::float as limite_o3,
                ROUND(AVG(p75_co)::numeric, 2)::float as limite_co
            FROM marts.fct_limites_de_contaminacion
            WHERE id_estacion = %(station_id)s
            GROUP BY id_estacion
        """
        df = pd.read_sql(query, engine, params={"station_id": station_id})

        if df.empty:
            # Si no hay límites, devolver límites OMS por defecto
            return {
                "limite_no2": 25.0,
                "limite_pm10": 45.0,
                "limite_pm25": 15.0,
                "limite_so2": 40.0,
                "limite_o3": 100.0,
                "limite_co": 10.0
            }

        return df.to_dict(orient="records")[0]
    except Exception as e:
        print(f"Error en limites: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener límites")


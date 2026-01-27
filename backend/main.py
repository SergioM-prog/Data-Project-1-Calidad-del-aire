from fastapi import FastAPI, HTTPException
from config import engine
import pandas as pd
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from sqlalchemy import types
from contextlib import asynccontextmanager
from database import init_db
import math
from fastapi import Query 
from sqlalchemy import text
#para probar mapa
from fastapi import APIRouter, HTTPException
from stations_coords import STATION_COORDS

@asynccontextmanager    # El decorador es un envoltorio funcional. Le dice a python que la función es un Gestor de Contexto (Context Manager) y tiene dos tiempos, una al arrancar (Antes del yield) y otra al apagar la api (Despues del yield)
async def lifespan(app: FastAPI):
    # --- CÓDIGO AL ARRANCAR EL CONTENEDOR ---
    try:
        init_db()
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

# # Modelos para objetos anidados del JSON. Así comprobamos que los valores dentro del diccionario son lo que deberían ser
# class GeoPoint(BaseModel):
#     lon: float
#     lat: float

# class GeoShape(BaseModel):
#     type: str
#     geometry: Dict[str, Any]
#     properties: Dict[str, Any]

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

# --- ENDPOINTS ---

@app.get("/health")
def health_check():
    """Endpoint para healthcheck de Docker."""
    return {"status": "ok"}

# Endpoint para recibir datos del script de Ingesta (POST)

@app.post("/api/ingest", status_code=201)
async def ingest_air_data(data: list[AirQualityInbound]):
    try:
        # 1. Convertimos la lista de modelos Pydantic a una lista de diccionarios Python
        # model_dump() es el estándar moderno de Pydantic v2
        payload = [item.model_dump() for item in data]
        
        # 2. Creamos el DataFrame. Al ser las llaves del JSON iguales a las 
        # columnas de la tabla, el mapeo es automático.
        df = pd.DataFrame(payload)
        
        # 3. Inserción en la tabla raw.valencia_air
        # Especificamos dtype para asegurar que los diccionarios se traten como JSONB
        df.to_sql(
            'valencia_air', 
            engine, 
            schema='raw', 
            if_exists='append', 
            index=False,
            dtype={
                'geo_shape': types.JSON,
                'geo_point_2d': types.JSON,
                'fecha_carg': types.DateTime(timezone=True)
            }
        )
        
        return {
            "status": "success", 
            "message": f"Se han insertado {len(df)} registros en columnas independientes."
        }
    
    except Exception as e:
        print(f"Error crítico en la ingesta: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Error al procesar la inserción en las columnas de la base de datos"
        )



# @app.get("/")
# def read_root():
#     return {"status": "ok", "message": "Air Quality API is running"}


# @app.get("/api/v1/hourly-metrics")
# def get_hourly_metrics(limit: int = 100):
#     """
#     Devuelve las últimas métricas horarias.
#     """
#     try:
#         # Usamos Pandas para leer SQL directamente. Es limpio y rápido.
#         query = f"SELECT * FROM marts.fct_air_quality_hourly ORDER BY measure_hour DESC LIMIT {limit}"
        
#         # Ejecutamos la consulta usando el engine de database.py
#         df = pd.read_sql(query, engine)
        
#         # Convertimos a diccionario (JSON)
#         return df.to_dict(orient="records")
        
#     except Exception as e:
#         print(f"Error en API: {e}")
#         raise HTTPException(status_code=500, detail="Error interno al leer base de datos")

@app.get("/api/v1/hourly-metrics")
def get_hourly_metrics(limit: int = Query(100, ge=1, le=5000)):
    """
    Devuelve las últimas métricas horarias (JSON seguro: sin NaN/Inf).
    """
    try:
        query = f"""
            SELECT *
            FROM marts.fct_air_quality_hourly
            ORDER BY measure_hour DESC
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

    
@app.get("/api/v1/alerts/now")
def get_alert_now(station_id: int = Query(..., ge=1)):
    """
    Devuelve el semáforo + recomendación actual para una estación,
    leyendo desde marts.fct_alertas_de_contaminacion.
    """
    try:
        q = text("""
            SELECT
                fecha_hora_alerta,
                id_estacion,
                nombre_estacion,
                nivel_severidad,
                contaminante_principal,
                descripcion_severidad,
                recomendacion
            FROM marts.fct_alertas_de_contaminacion
            WHERE id_estacion = :station_id
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

@app.get("/api/v1/station/latest-hourly")
def get_station_latest_hourly(station_id: int = Query(..., ge=1)):
    """
    Devuelve la fila más reciente (última hora) de marts.fct_air_quality_hourly para una estación.
    """
    try:
        query = """
            SELECT *
            FROM marts.fct_air_quality_hourly
            WHERE station_id = %(station_id)s
            ORDER BY measure_hour DESC
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

#PARA PROBAR MAPA 

@app.get("/air_quality/history")
def air_quality_history(station_id: int, window: str = "now"):
    rows = []

    # --- tu lógica actual de histórico ---
    rows.append({
        "timestamp": "2026-01-26T10:00:00",
        "nivel_severidad": 3,
    })


    coords = STATION_COORDS.get(station_id)
    if coords:
        for r in rows:
            r["lat"] = coords["lat"]
            r["lon"] = coords["lon"]

    return rows


@app.get("/api/v1/stations")
def get_stations():
    """
    Devuelve la lista de estaciones únicas con su ID y nombre.
    """
    try:
        query = """
            SELECT DISTINCT station_id, station_name
            FROM marts.fct_air_quality_hourly
            WHERE station_name IS NOT NULL
            ORDER BY station_name
        """
        df = pd.read_sql(query, engine)
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"Error en stations: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener estaciones")


@app.get("/api/v1/zonas-verdes")
def get_zonas_verdes(limit: int = Query(3, ge=1, le=10)):
    """
    Devuelve las estaciones con mejor calidad del aire (menor contaminación).
    Solo incluye estaciones donde NINGÚN contaminante supere su umbral.
    Umbrales: NO2=25, PM2.5=15, PM10=45, O3=100, SO2=40 µg/m³
    """
    try:
        query = """
            WITH ultimas_mediciones AS (
                SELECT DISTINCT ON (station_id)
                    station_id,
                    station_name,
                    avg_no2,
                    avg_pm25,
                    avg_pm10,
                    avg_o3,
                    avg_so2,
                    measure_hour
                FROM marts.fct_air_quality_hourly
                ORDER BY station_id, measure_hour DESC
            ),
            sin_alertas AS (
                SELECT
                    station_id,
                    station_name,
                    measure_hour,
                    avg_no2,
                    avg_pm25,
                    avg_pm10,
                    avg_o3,
                    avg_so2,
                    COALESCE(avg_no2, 0) + COALESCE(avg_pm25, 0) + COALESCE(avg_pm10, 0) +
                    COALESCE(avg_o3, 0) + COALESCE(avg_so2, 0) AS indice_contaminacion
                FROM ultimas_mediciones
                WHERE station_name IS NOT NULL
                  AND (avg_no2 IS NULL OR avg_no2 <= 25)
                  AND (avg_pm25 IS NULL OR avg_pm25 <= 15)
                  AND (avg_pm10 IS NULL OR avg_pm10 <= 45)
                  AND (avg_o3 IS NULL OR avg_o3 <= 100)
                  AND (avg_so2 IS NULL OR avg_so2 <= 40)
            )
            SELECT
                station_id,
                station_name,
                avg_no2,
                avg_pm25,
                avg_pm10,
                avg_o3,
                avg_so2,
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

    
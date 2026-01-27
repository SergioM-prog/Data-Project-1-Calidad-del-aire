from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
from config import engine
import pandas as pd
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from sqlalchemy import types, text
from contextlib import asynccontextmanager
from database import init_db, load_historical_real_data, load_historical_simulated_data
from sqlalchemy.dialects.postgresql import insert


# ----------------------------------

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



# --- ENDPOINTS DE ALERTAS ---

@app.get("/api/alertas")
async def get_alertas_pendientes():
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
async def registrar_alerta_enviada(alertas: list[dict]):
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
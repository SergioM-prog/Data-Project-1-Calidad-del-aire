from fastapi import FastAPI, HTTPException
from config import engine  # <--- Importamos la conexión desde el archivo vecino
import pandas as pd
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from sqlalchemy import types

# 1. Inicialización de la API
app = FastAPI(
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
    # 'forbid' asegura que no aceptamos ningún campo que no esté en esta lista
    model_config = ConfigDict(extra='forbid')

# --- ENDPOINTS ---

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
                'geo_point_2d': types.JSON
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
from fastapi import FastAPI, HTTPException
from database import engine  # <--- Importamos la conexión desde el archivo vecino
import pandas as pd
from sqlalchemy import text

app = FastAPI(title="Air Quality API", version="1.0.0")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Air Quality API is running"}

@app.get("/api/v1/hourly-metrics")
def get_hourly_metrics(limit: int = 100):
    """
    Devuelve las últimas métricas horarias.
    """
    try:
        # Usamos Pandas para leer SQL directamente. Es limpio y rápido.
        query = f"SELECT * FROM marts.fct_air_quality_hourly ORDER BY measure_hour DESC LIMIT {limit}"
        
        # Ejecutamos la consulta usando el engine de database.py
        df = pd.read_sql(query, engine)
        
        # Convertimos a diccionario (JSON)
        return df.to_dict(orient="records")
        
    except Exception as e:
        print(f"Error en API: {e}")
        raise HTTPException(status_code=500, detail="Error interno al leer base de datos")
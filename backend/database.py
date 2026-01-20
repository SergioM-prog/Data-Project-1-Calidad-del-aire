from sqlalchemy import text
from config import engine # Importamos el engine centralizado
import time

def init_db():
    """Inicializa la infraestructura de la base de datos (esquemas y tablas)."""
    for i in range(10):
        try:
            # Usamos engine.connect() y manejamos la transacción manualmente
            with engine.connect() as conn:
                print(f"Intento {i+1}: Conectado con SQLAlchemy. Configurando esquemas...")
                
                # 1. Creación de esquemas (Capas de Medallón)
                # Es obligatorio usar text() para ejecutar strings en SQLAlchemy

                conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw;"))
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging;"))
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS intermediate;"))
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS marts;"))

                # 2. Tabla para Valencia
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS raw.valencia_air (
                        id SERIAL PRIMARY KEY,
                        ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        objectid INTEGER,
                        nombre VARCHAR(255),
                        direccion TEXT,
                        tipozona VARCHAR(100),
                        parametros TEXT,
                        mediciones TEXT,
                        so2 NUMERIC,
                        no2 NUMERIC,
                        o3 NUMERIC,
                        co NUMERIC,
                        pm10 NUMERIC,
                        pm25 NUMERIC,
                        tipoemisio VARCHAR(100),
                        fecha_carg TIMESTAMPTZ,
                        calidad_am VARCHAR(100),
                        fiwareid VARCHAR(255),
                        geo_shape JSONB,
                        geo_point_2d JSONB
                    );
                """))
                
                conn.commit() 
                print("✅ Base de datos lista: Esquemas y tablas RAW creados correctamente.")
                return 

        except Exception as e:
            print(f"⚠️ Intento {i+1} fallido: {e}")
            time.sleep(2)

    raise RuntimeError("No se pudo conectar a la base de datos tras 10 intentos.")
import os

# 1. Configuración de la Base de Datos
# Sacamos los datos de las variables de entorno definidas en el docker-compose / .env
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_HOST = os.getenv("POSTGRES_HOST", "db")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "air_quality_db")

# Construimos la URL de conexión
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 2. Diccionario de Configuración por Ciudad
# Centralizamos las URLs y los nombres de las tablas en un diccionario
# Esto facilita que el orquestador (main.py) pueda hacer un bucle.
CITIES_CONFIG = {
    "valencia": {
        "api_url": "https://valencia.opendatasoft.com/api/explore/v2.1/catalog/datasets/estacions-contaminacio-atmosferiques-estaciones-contaminacion-atmosfericas/records?limit=20",
        "table_name": "raw_valencia_air",
        "active": True
    },
    "madrid": {
        "api_url": "https://datos.madrid.es/egob/catalogo/212504-0-calidad-aire-tiempo-real.json",
        "table_name": "raw_madrid_air",
        "active": True
    },
    "pais_vasco": {
        "api_url": "https://opendata.euskadi.eus/api-air-quality/",
        "table_name": "raw_pais_vasco_air",
        "active": False
    }
}

# 3. Configuración Global de Ingesta
RETRY_ATTEMPTS = 3
TIMEOUT_SECONDS = 10
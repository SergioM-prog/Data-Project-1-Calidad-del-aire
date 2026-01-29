import os

# 1. Diccionario de Configuración por Ciudad
# Centralizamos las URLs y los nombres de las tablas en un diccionario
# Esto facilita que el orquestador (main.py) pueda hacer un bucle.
CITIES_CONFIG = {
    "valencia": {
        "api_url": "https://valencia.opendatasoft.com/api/explore/v2.1/catalog/datasets/estacions-contaminacio-atmosferiques-estaciones-contaminacion-atmosfericas/records?limit=20",
        "table_name": "raw_valencia_air",
        "active": True
    },
}

# La URL del endpoint de ingestion de la api backend
BARRIER_API_URL = os.getenv("BARRIER_API_URL")

# API Key para autenticación M2M
API_KEY = os.getenv("INGESTION_VALENCIA_API_KEY")

# 2. Configuración Global de Ingesta
RETRY_ATTEMPTS = 3
TIMEOUT_SECONDS = 10
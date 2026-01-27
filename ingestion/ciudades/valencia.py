import requests
from utils import f_llamada_api
from config import API_KEY

# Headers para autenticación M2M
AUTH_HEADERS = {"X-API-Key": API_KEY}

def f_run_ingestion_valencia(valencia_api_url, barrier_api_url):
    """
    1. Obtiene datos de la API de Valencia.
    2. Los envía a nuestra API de Barrera mediante un POST.
    """
    try:
        # --- PASO 1: Obtener datos de la fuente original ---
        print(f">> Conectando con Valencia_API...")
        response = f_llamada_api(valencia_api_url, "Valencia_API")
        data = response.json()
        estaciones = data.get('results', [])

        if not estaciones:
            print("⚠️ No se han obtenido estaciones de la API de Valencia.")
            return

        # --- PASO 2: Enviar los datos a nuestra API de Barrera ---
        # barrier_api_url será algo como "http://backend:8000/api/ingest"
        print(f">> Enviando {len(estaciones)} estaciones a la API de Barrera...")

        # Enviamos la lista completa de estaciones.
        # FastAPI la validará automáticamente con la clase AirQualityInbound
        api_response = requests.post(barrier_api_url, headers=AUTH_HEADERS, json=estaciones)

        # --- PASO 3: Verificar el resultado ---
        if api_response.status_code == 201:
            resultado = api_response.json()
            print(f"✅ Éxito: {resultado.get('message')}")
        else:
            print(f"❌ Error en la API de Barrera (Status {api_response.status_code}): {api_response.text}")

    except Exception as e:
        print(f"❌ Error crítico en el flujo de ingesta: {e}")
        raise
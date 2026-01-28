import os
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from config import CITIES_CONFIG, BARRIER_API_URL
from ciudades import f_run_ingestion_valencia
# from ciudades import f_run_ingestion_madrid

# Mapeo de funciones: asocia el nombre de la ciudad con su función de ingesta
INGESTION_MAP = {
    "valencia": f_run_ingestion_valencia,
    # "madrid": f_run_ingestion_madrid,
}


def run_single_ingestion(city, settings, func):
    """
    Ejecuta una única ingesta para la ciudad especificada.
    Retorna True si fue exitosa, False si hubo error.
    """
    print(f"--- INGESTA: {city.upper()} ---")
    try:
        func(settings["api_url"], f"{BARRIER_API_URL}/api/ingest")
        print(f"✅ Completado: {city}")
        return True
    except Exception as e:
        print(f"❌ Error en ingesta de {city}: {e}")
        return False


def main():
    """
    Ejecuta la ingesta para la ciudad especificada en la variable de entorno CITY.
    Cada contenedor Docker define su propia variable CITY.
    El proceso se ejecuta en un bucle infinito cada 30 minutos.
    """
    city = os.getenv("CITY")

    if not city:
        print("ERROR: Variable de entorno CITY no definida")
        sys.exit(1)

    settings = CITIES_CONFIG.get(city)
    if not settings:
        print(f"ERROR: Ciudad '{city}' no existe en CITIES_CONFIG")
        sys.exit(1)

    func = INGESTION_MAP.get(city)
    if not func:
        print(f"ERROR: No hay funcion de ingesta registrada para '{city}'")
        sys.exit(1)

    # Configuración del intervalo de ingesta
    INTERVAL_SECONDS = 1800  # 30 minutos
    SPAIN_TZ = ZoneInfo("Europe/Madrid")

    def get_spain_time():
        """Devuelve la hora actual en España"""
        return datetime.now(SPAIN_TZ)

    print(f"🚀 Iniciando servicio de ingesta para {city.upper()}")
    print(f"📅 Frecuencia: cada {INTERVAL_SECONDS // 60} minutos")
    print(f"⏰ Hora de inicio: {get_spain_time().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    iteration = 0
    while True:
        iteration += 1
        current_time = get_spain_time()
        print(f"\n[Iteración #{iteration}] {current_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Ejecutar ingesta
        success = run_single_ingestion(city, settings, func)

        # Mostrar resultado y próxima ejecución
        next_time = datetime.now(SPAIN_TZ).timestamp() + INTERVAL_SECONDS
        next_run = datetime.fromtimestamp(next_time, SPAIN_TZ).strftime('%H:%M:%S')
        if success:
            print(f"⏳ Próxima ingesta a las {next_run} (en {INTERVAL_SECONDS // 60} minutos)")
        else:
            print(f"⚠️ Reintentando en {INTERVAL_SECONDS // 60} minutos (a las {next_run})")

        print("=" * 60)

        # Esperar antes de la siguiente iteración
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    # Delay para asegurar que Postgres y Backend han arrancado
    time.sleep(5)
    main()
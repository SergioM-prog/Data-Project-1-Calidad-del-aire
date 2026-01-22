import os
import sys
import time
from config import CITIES_CONFIG, BARRIER_API_URL
from ciudades import f_run_ingestion_valencia
# from ciudades import f_run_ingestion_madrid

# Mapeo de funciones: asocia el nombre de la ciudad con su función de ingesta
INGESTION_MAP = {
    "valencia": f_run_ingestion_valencia,
    # "madrid": f_run_ingestion_madrid,
}


def main():
    """
    Ejecuta la ingesta para la ciudad especificada en la variable de entorno CITY.
    Cada contenedor Docker define su propia variable CITY.
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

    print(f"--- INGESTA: {city.upper()} ---")
    try:
        func(settings["api_url"], BARRIER_API_URL)
        print(f"Completado: {city}")
    except Exception as e:
        print(f"Error en ingesta de {city}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Delay para asegurar que Postgres y Backend han arrancado
    time.sleep(5)
    main()
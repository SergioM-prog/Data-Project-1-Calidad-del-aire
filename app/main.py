import time
from config import DATABASE_URL, CITIES_CONFIG
from database import f_crear_tablas
# Importamos las funciones de ingesta de cada ciudad
from ingestion import f_run_ingestion_valencia, f_run_ingestion_madrid

# 1. Mapeo de funciones
# Este diccionario asocia el nombre de la ciudad en config.py con su función real
INGESTION_MAP = {
    "valencia": f_run_ingestion_valencia,
    "madrid": f_run_ingestion_madrid,
}

def orquestador():
    print("--- INICIANDO ORQUESTADOR DE CALIDAD DEL AIRE ---")
    
    # PASO 1: Asegurar que las tablas existen antes de empezar
    print("Verificando infraestructura de base de datos...")
    try:
        f_crear_tablas(DATABASE_URL)
        print("✅ Tablas verificadas/creadas.")
    except Exception as e:
        print(f"❌ Error crítico al crear tablas: {e}")
        return

    # PASO 2: Iterar por las ciudades configuradas
    for city_name, settings in CITIES_CONFIG.items():
        if not settings.get("active", False):
            print(f"Propiedad 'active' en False para {city_name}. Saltando...")
            continue
            
        print(f"\n>> Procesando ciudad: {city_name.upper()}")
        
        # Obtenemos la función específica del diccionario
        func_ingesta = INGESTION_MAP.get(city_name)
        
        if func_ingesta:
            try:
                # Ejecutamos la ingesta pasándole su URL y la DB
                func_ingesta(DATABASE_URL, settings["api_url"])
                print(f"✅ Finalizada ingesta de {city_name}.")
            except Exception as e:
                # Si una ciudad falla, el bucle sigue con la siguiente
                print(f"⚠️ Error procesando {city_name}: {e}")
        else:
            print(f"❌ No se encontró una función de ingesta para {city_name}.")

    print("\n--- PROCESO DE INGESTA FINALIZADO ---")

if __name__ == "__main__":
    #Delay para asegurar que Postgres ha arrancado en Docker
    time.sleep(5) 
    orquestador()
import psycopg, time

def f_conexion_bd(db_url, db_nombre):
    for i in range(10):
        try:            
            connection = psycopg.connect(db_url)
            print(f"BD {db_nombre} conectada con éxito")
            return connection
        
        except psycopg.OperationalError as e:
            print(f"Intento {i+1}: la BD {db_nombre} aún no está lista. Esperando...")
            time.sleep(2)
    raise RuntimeError(f"No se pudo conectar a la BD {db_nombre} tras 10 intentos")

def f_crear_tablas(database_url):
    conn = f_conexion_bd(database_url, "Schema_Setup")
    cur = conn.cursor()

    try:
        # 1. Creación de esquemas (Capas de Medallón)
        print("Creando estructura de esquemas (raw, staging, marts)...")
        cur.execute("CREATE SCHEMA IF NOT EXISTS raw;")
        cur.execute("CREATE SCHEMA IF NOT EXISTS staging;")
        cur.execute("CREATE SCHEMA IF NOT EXISTS intermediate;")
        cur.execute("CREATE SCHEMA IF NOT EXISTS marts;")

        # 2. Tabla para Valencia (En esquema 'raw')
        cur.execute("""
            CREATE TABLE IF NOT EXISTS raw.valencia_air (
                id SERIAL PRIMARY KEY,
                station_id INTEGER NOT NULL,
                data_raw JSONB,
                timestamp TIMESTAMP WITH TIME ZONE
            );
        """)

        # 3. Tabla para Madrid (ahora en esquema 'raw')
        cur.execute("""
            CREATE TABLE IF NOT EXISTS raw.madrid_air (
                id SERIAL PRIMARY KEY,
                station_id INTEGER,
                data_raw JSONB,
                timestamp TIMESTAMP WITH TIME ZONE
            );
        """)

        conn.commit()
        print("✅ Infraestructura de esquemas y tablas RAW preparada.")
        
    except Exception as e:
        print(f"❌ Error creando infraestructura: {e}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
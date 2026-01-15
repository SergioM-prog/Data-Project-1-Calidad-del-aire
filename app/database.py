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
        # Tabla para Valencia
        cur.execute("""
            CREATE TABLE IF NOT EXISTS raw_valencia_air (
                id SERIAL PRIMARY KEY,
                station_id INTEGER NOT NULL,
                data_raw JSONB,                    -- Aquí guardamos TODO el objeto de la estación
                timestamp TIMESTAMP WITH TIME ZONE -- Mantenemos esto para facilitar filtros temporales
            );
        """)

        # Tabla para Madrid
        cur.execute("""
            CREATE TABLE IF NOT EXISTS raw_madrid_air (
                id SERIAL PRIMARY KEY,
                station_id INTEGER,
                data_raw JSONB,
                timestamp TIMESTAMP WITH TIME ZONE
            );
        """)

        conn.commit()
        print("✅ Infraestructura JSONB preparada. El sistema es ahora 100% dinámico.")
    except Exception as e:
        print(f"❌ Error creando tablas: {e}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
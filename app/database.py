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

                -- Campos tipo diccionario (se guardan como JSONB sin extraer nada)
                geo_shape JSONB,
                geo_point_2d JSONB
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
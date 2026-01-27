from sqlalchemy import text, types
from config import engine # Importamos el engine centralizado
import time
import pandas as pd
import os
from pathlib import Path

# Diccionario con los metadatos de cada estación (basado en la API de Valencia)
# La clave es el objectid (nombre del archivo CSV)

STATIONS_METADATA = {
    12: {
        "nombre": "Dr. Lluch",
        "direccion": "DR.LLUCH",
        "tipozona": "Urbana",
        "tipoemisio": "Tráfico",
        "fiwareid": "A08_DR_LLUCH_60m",
        "geo_shape": {"type": "Feature", "geometry": {"coordinates": [-0.328289489402739, 39.4666847554611], "type": "Point"}, "properties": {}},
        "geo_point_2d": {"lon": -0.328289489402739, "lat": 39.4666847554611}
    },
    13: {
        "nombre": "Francia",
        "direccion": "AVDA.FRANCIA",
        "tipozona": "Urbana",
        "tipoemisio": "Tráfico",
        "fiwareid": "A01_AVFRANCIA_60m",
        "geo_shape": {"type": "Feature", "geometry": {"coordinates": [-0.342986232422652, 39.4578268875183], "type": "Point"}, "properties": {}},
        "geo_point_2d": {"lon": -0.342986232422652, "lat": 39.4578268875183}
    },
    14: {
        "nombre": "Boulevar Sur",
        "direccion": "BULEVARD SUD",
        "tipozona": "Urbana",
        "tipoemisio": "Tráfico",
        "fiwareid": "A02_BULEVARDSUD_60m",
        "geo_shape": {"type": "Feature", "geometry": {"coordinates": [-0.396337564375856, 39.4503960055054], "type": "Point"}, "properties": {}},
        "geo_point_2d": {"lon": -0.396337564375856, "lat": 39.4503960055054}
    },
    15: {
        "nombre": "Molí del Sol",
        "direccion": "MOLÍ DEL SOL",
        "tipozona": "Suburbana",
        "tipoemisio": "Tráfico",
        "fiwareid": "A03_MOLISOL_60m",
        "geo_shape": {"type": "Feature", "geometry": {"coordinates": [-0.408809896900938, 39.4811121109041], "type": "Point"}, "properties": {}},
        "geo_point_2d": {"lon": -0.408809896900938, "lat": 39.4811121109041}
    },
    16: {
        "nombre": "Pista de Silla",
        "direccion": "PISTA DE SILLA",
        "tipozona": "Urbana",
        "tipoemisio": "Tráfico",
        "fiwareid": "A04_PISTASILLA_60m",
        "geo_shape": {"type": "Feature", "geometry": {"coordinates": [-0.376643936579157, 39.4580609536967], "type": "Point"}, "properties": {}},
        "geo_point_2d": {"lon": -0.376643936579157, "lat": 39.4580609536967}
    },
    17: {
        "nombre": "Universidad Politécnica",
        "direccion": "POLITÈCNIC",
        "tipozona": "Suburbana",
        "tipoemisio": "Fondo",
        "fiwareid": "A05_POLITECNIC_60m",
        "geo_shape": {"type": "Feature", "geometry": {"coordinates": [-0.337400660521869, 39.4796444969292], "type": "Point"}, "properties": {}},
        "geo_point_2d": {"lon": -0.337400660521869, "lat": 39.4796444969292}
    },
    18: {
        "nombre": "Viveros",
        "direccion": "VIVERS",
        "tipozona": "Urbana",
        "tipoemisio": "Fondo",
        "fiwareid": "A06_VIVERS_60m",
        "geo_shape": {"type": "Feature", "geometry": {"coordinates": [-0.36964822314381, 39.4796409248053], "type": "Point"}, "properties": {}},
        "geo_point_2d": {"lon": -0.36964822314381, "lat": 39.4796409248053}
    },
    19: {
        "nombre": "Centro",
        "direccion": "VALÈNCIA CENTRE",
        "tipozona": "Urbana",
        "tipoemisio": "Tráfico",
        "fiwareid": "A07_VALENCIACENTRE_60m",
        "geo_shape": {"type": "Feature", "geometry": {"coordinates": [-0.376397651655324, 39.4705476702601], "type": "Point"}, "properties": {}},
        "geo_point_2d": {"lon": -0.376397651655324, "lat": 39.4705476702601}
    },
    20: {
        "nombre": "Cabanyal",
        "direccion": "CABANYAL",
        "tipozona": "Urbana",
        "tipoemisio": "Fondo",
        "fiwareid": "A09_CABANYAL_60m",
        "geo_shape": {"type": "Feature", "geometry": {"coordinates": [-0.328534813492744, 39.4743907853568], "type": "Point"}, "properties": {}},
        "geo_point_2d": {"lon": -0.328534813492744, "lat": 39.4743907853568}
    },
    21: {
        "nombre": "Olivereta",
        "direccion": "OLIVERETA",
        "tipozona": "Urbana",
        "tipoemisio": "Tráfico",
        "fiwareid": "A10_OLIVERETA_60m",
        "geo_shape": {"type": "Feature", "geometry": {"coordinates": [-0.405923445529068, 39.469244235092], "type": "Point"}, "properties": {}},
        "geo_point_2d": {"lon": -0.405923445529068, "lat": 39.469244235092}
    },
    22: {
        "nombre": "Patraix",
        "direccion": "PATRAIX",
        "tipozona": "Urbana",
        "tipoemisio": "Tráfico",
        "fiwareid": "A11_PATRAIX_60m",
        "geo_shape": {"type": "Feature", "geometry": {"coordinates": [-0.401411329219129, 39.4591890899964], "type": "Point"}, "properties": {}},
        "geo_point_2d": {"lon": -0.401411329219129, "lat": 39.4591890899964}
    },
}

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
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS alerts;"))
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS security;"))

                # 2. Tabla para Valencia (datos en tiempo real de la API)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS raw.valencia_air_real_hourly (
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
                        geo_point_2d JSONB,
                        UNIQUE(objectid, fecha_carg)
                    );
                """))

                # 3. Tabla para datos históricos reales diarios de Valencia del 01/01/2014 al 31/10/2025 (cargados desde los CSV de la ruta historical/real)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS raw.valencia_air_historical_real_daily (
                        id SERIAL PRIMARY KEY,
                        ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        objectid INTEGER,
                        nombre VARCHAR(255),
                        direccion TEXT,
                        tipozona VARCHAR(100),
                        tipoemisio VARCHAR(100),
                        fiwareid VARCHAR(255),
                        fecha_medicion TIMESTAMPTZ,
                        so2 NUMERIC,
                        no2 NUMERIC,
                        o3 NUMERIC,
                        co NUMERIC,
                        pm10 NUMERIC,
                        pm25 NUMERIC,
                        geo_shape JSONB,
                        geo_point_2d JSONB
                    );
                """))

                # 4. Tabla para datos históricos simulados horarios de Valencia del 01/01/2025 al 31/01/2026 (cargados desde los CSV de la ruta historical/simulated)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS raw.valencia_air_historical_simulated_hourly (
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
                        geo_point_2d JSONB,
                        UNIQUE(objectid, fecha_carg)
                    );
                """))

                # 5. Tabla para registro de alertas enviadas a Telegram (histórico permanente)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS alerts.alertas_enviadas_telegram (
                        id SERIAL PRIMARY KEY,
                        fecha_envio TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        id_estacion INTEGER NOT NULL,
                        fecha_hora_alerta TIMESTAMPTZ NOT NULL,
                        nombre_estacion VARCHAR(255),
                        ciudad VARCHAR(100),
                        parametro VARCHAR(10) NOT NULL,
                        valor NUMERIC,
                        limite NUMERIC,
                        UNIQUE(id_estacion, fecha_hora_alerta, parametro)
                    );
                """))

                # 6. Tabla para autenticación M2M (Machine-to-Machine)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS security.api_key_clients (
                        id SERIAL PRIMARY KEY,
                        service_name VARCHAR(100) UNIQUE NOT NULL,
                        api_key VARCHAR(255) UNIQUE NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    );
                """))

                # Índice para búsquedas rápidas por api_key
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_api_key_clients_api_key
                    ON security.api_key_clients(api_key);
                """))

                conn.commit() 
                print("✅ Base de datos lista: Esquemas y tablas RAW creados correctamente.")
                return 

        except Exception as e:
            print(f"⚠️ Intento {i+1} fallido: {e}")
            time.sleep(2)

    raise RuntimeError("No se pudo conectar a la base de datos tras 10 intentos.")


def load_historical_real_data(historical_path: str = "", table_name: str = ""):
    """table_name
    Carga los datos históricos desde archivos CSV a la tabla de históricos del esquema raw.
    Solo se ejecuta si la tabla está vacía (carga única).

    Args:
        historical_path: Ruta al directorio con los archivos CSV históricos
        table_name: tabla en la db a la que cargar los históricos
    """
    try:
        with engine.connect() as conn:
            # Verificar si ya hay datos históricos cargados
            result = conn.execute(text(f"SELECT COUNT(*) FROM raw.{table_name}"))
            count = result.scalar()

            if count > 0:
                print(f"⏭️ Datos históricos ya cargados ({count} registros). Saltando carga.")
                return

            # Verificar si existe el directorio de históricos
            historical_dir = Path(historical_path)
            if not historical_dir.exists():
                print(f"⚠️ Directorio de históricos no encontrado: {historical_path}")
                return

            # Buscar archivos CSV
            csv_files = list(historical_dir.glob("*.csv"))
            if not csv_files:
                print(f"⚠️ No se encontraron archivos CSV en {historical_path}")
                return

            print(f">> Iniciando carga de {len(csv_files)} archivos históricos...")
            total_records = 0

            for csv_file in csv_files:
                try:
                    # Extraer objectid del nombre del archivo (ej: "13.csv" -> 13)
                    objectid = int(csv_file.stem)

                    # Verificar que tenemos metadatos para esta estación
                    if objectid not in STATIONS_METADATA:
                        print(f"⚠️ No hay metadatos para estación {objectid}. Saltando {csv_file.name}")
                        continue

                    metadata = STATIONS_METADATA[objectid]

                    # Leer CSV con configuración específica para estos archivos
                    # - Separador: punto y coma
                    # - Decimales con coma
                    # - Encoding latin-1 para caracteres especiales
                    df = pd.read_csv(
                        csv_file,
                        sep=';',
                        decimal=',',
                        encoding='latin-1',
                        na_values=['', ' ']
                    )

                    # Normalizar nombres de columnas (quitar unidades y espacios)
                    column_mapping = {}
                    for col in df.columns:
                        col_lower = col.lower()
                        if 'fecha' in col_lower:
                            column_mapping[col] = 'fecha_medicion'
                        elif 'pm2.5' in col_lower or 'pm2,5' in col_lower:
                            column_mapping[col] = 'pm25'
                        elif 'pm10' in col_lower:
                            column_mapping[col] = 'pm10'
                        elif 'so2' in col_lower:
                            column_mapping[col] = 'so2'
                        elif 'co' in col_lower and 'veloc' not in col_lower:
                            column_mapping[col] = 'co'
                        elif 'no2' in col_lower:
                            column_mapping[col] = 'no2'
                        elif 'ozono' in col_lower or 'o3' in col_lower:
                            column_mapping[col] = 'o3'
                        # Ignoramos NO, NOx y Veloc. ya que no están en la tabla

                    df = df.rename(columns=column_mapping)

                    # Convertir fecha de dd/mm/yyyy a formato date
                    if 'fecha_medicion' in df.columns:
                        df['fecha_medicion'] = pd.to_datetime(
                            df['fecha_medicion'],
                            format='%d/%m/%Y',
                            errors='coerce'
                        ).dt.date

                    # Seleccionar solo las columnas que necesitamos
                    columns_to_keep = ['fecha_medicion', 'pm25', 'pm10', 'so2', 'co', 'no2', 'o3']
                    available_columns = [col for col in columns_to_keep if col in df.columns]
                    df = df[available_columns].copy()

                    # Añadir metadatos de la estación
                    df['objectid'] = objectid
                    df['nombre'] = metadata['nombre']
                    df['direccion'] = metadata['direccion']
                    df['tipozona'] = metadata['tipozona']
                    df['tipoemisio'] = metadata['tipoemisio']
                    df['fiwareid'] = metadata['fiwareid']
                    df['geo_shape'] = [metadata['geo_shape']] * len(df)
                    df['geo_point_2d'] = [metadata['geo_point_2d']] * len(df)

                    # Eliminar filas sin fecha válida
                    df = df.dropna(subset=['fecha_medicion'])

                    if len(df) == 0:
                        print(f"⚠️ No hay datos válidos en {csv_file.name}")
                        continue

                    # Insertar en la base de datos
                    
                    df.to_sql(
                        f'{table_name}',
                        engine,
                        schema='raw',
                        if_exists='append',
                        index=False,
                        dtype={
                            'geo_shape': types.JSON,
                            'geo_point_2d': types.JSON
                        }
                    )

                    total_records += len(df)
                    print(f"✅ {csv_file.name}: {len(df)} registros cargados ({metadata['nombre']})")

                except Exception as e:
                    print(f"  ❌ Error procesando {csv_file.name}: {e}")
                    continue

            print(f"✅ Carga histórica completada: {total_records} registros totales insertados.")

    except Exception as e:
        print(f"❌ Error en la carga de datos históricos: {e}")
        raise


def load_historical_simulated_data(historical_path: str = "", table_name: str = ""):
    """
    Carga los datos históricos simulados desde archivos CSV a la tabla del esquema raw.
    Solo se ejecuta si la tabla está vacía.

    Nota: Los archivos CSV simulados ya contienen todos los metadatos (objectid, nombre,
    geo_shape, etc.) en un único archivo con todas las estaciones.
    """
    import json

    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM raw.{table_name}"))
            if result.scalar() > 0:
                print(f"⏭️ Datos históricos simulados ya cargados. Saltando carga.")
                return

        historical_dir = Path(historical_path)
        if not historical_dir.exists():
            print(f"⚠️ Directorio no encontrado: {historical_path}")
            return

        csv_files = list(historical_dir.glob("*.csv"))
        if not csv_files:
            print(f"⚠️ No se encontraron archivos CSV en {historical_path}")
            return

        print(f">> Cargando {len(csv_files)} archivos históricos simulados...")
        total_records = 0

        for csv_file in csv_files:
            try:
                # Leer CSV en chunks para evitar problemas de memoria
                chunk_size = 10000
                chunks_loaded = 0

                for chunk in pd.read_csv(csv_file, encoding='utf-8', na_values=['', ' '], chunksize=chunk_size):
                    # Convertir fecha_carg de string a datetime
                    if 'fecha_carg' in chunk.columns:
                        chunk['fecha_carg'] = pd.to_datetime(chunk['fecha_carg'], errors='coerce')

                    # Convertir columnas geo_shape y geo_point_2d de string JSON a dict
                    if 'geo_shape' in chunk.columns:
                        chunk['geo_shape'] = chunk['geo_shape'].apply(lambda x: json.loads(x) if pd.notna(x) and isinstance(x, str) else x)
                    if 'geo_point_2d' in chunk.columns:
                        chunk['geo_point_2d'] = chunk['geo_point_2d'].apply(lambda x: json.loads(x) if pd.notna(x) and isinstance(x, str) else x)

                    chunk.to_sql(
                        table_name, engine, schema='raw', if_exists='append', index=False,
                        dtype={
                            'geo_shape': types.JSON,
                            'geo_point_2d': types.JSON,
                            'fecha_carg': types.DateTime(timezone=True)
                        }
                    )

                    chunks_loaded += len(chunk)
                    total_records += len(chunk)

                print(f"  ✅ {csv_file.name}: {chunks_loaded} registros cargados")

            except Exception as e:
                print(f"  ❌ Error en {csv_file.name}: {e}")
                import traceback
                traceback.print_exc()

        print(f"✅ Carga completada: {total_records} registros insertados.")

    except Exception as e:
        print(f"❌ Error en carga de históricos simulados: {e}")
        import traceback
        traceback.print_exc()
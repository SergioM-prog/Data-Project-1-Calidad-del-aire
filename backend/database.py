from sqlalchemy import text
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

                # 2. Tabla para Valencia (datos en tiempo real de la API)
                conn.execute(text("""
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
                        geo_shape JSONB,
                        geo_point_2d JSONB,
                        UNIQUE(objectid, fecha_carg)
                    );
                """))

                # 3. Tabla para datos históricos de Valencia (cargados desde CSVs)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS raw.valencia_air_historical (
                        id SERIAL PRIMARY KEY,
                        ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        objectid INTEGER,
                        nombre VARCHAR(255),
                        direccion TEXT,
                        tipozona VARCHAR(100),
                        tipoemisio VARCHAR(100),
                        fiwareid VARCHAR(255),
                        fecha_medicion DATE,
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
                
                conn.commit() 
                print("✅ Base de datos lista: Esquemas y tablas RAW creados correctamente.")
                return 

        except Exception as e:
            print(f"⚠️ Intento {i+1} fallido: {e}")
            time.sleep(2)

    raise RuntimeError("No se pudo conectar a la base de datos tras 10 intentos.")


def load_historical_data(historical_path: str = "/app/historical"):
    """
    Carga los datos históricos desde archivos CSV a la tabla raw.valencia_air_historical.
    Solo se ejecuta si la tabla está vacía (carga única).

    Args:
        historical_path: Ruta al directorio con los archivos CSV históricos
    """
    try:
        with engine.connect() as conn:
            # Verificar si ya hay datos históricos cargados
            result = conn.execute(text("SELECT COUNT(*) FROM raw.valencia_air_historical"))
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
                    from sqlalchemy import types
                    df.to_sql(
                        'valencia_air_historical',
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
                    print(f"  ✅ {csv_file.name}: {len(df)} registros cargados ({metadata['nombre']})")

                except Exception as e:
                    print(f"  ❌ Error procesando {csv_file.name}: {e}")
                    continue

            print(f"✅ Carga histórica completada: {total_records} registros totales insertados.")

    except Exception as e:
        print(f"❌ Error en la carga de datos históricos: {e}")
        raise
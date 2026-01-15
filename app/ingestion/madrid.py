import xml.etree.ElementTree as ET
import psycopg
from psycopg.types.json import Json
from database import f_conexion_bd
from utils import f_llamada_api

def f_run_ingestion_madrid(database_url, api_url):
    connection = f_conexion_bd(database_url, "Madrid_XML_Ingestion")
    
    with connection.cursor() as cur:
        try:
            # Llamada a la API (Devuelve el XML de sensores)
            response = f_llamada_api(api_url, "Madrid_API")
            
            # Parseamos el contenido XML
            root = ET.fromstring(response.content)
            
            # El XML de Madrid tiene una etiqueta <medicion> por cada sensor/estación
            mediciones = root.findall('medicion')
            print(f"Procesando {len(mediciones)} registros de sensores de Madrid (XML)...")

            query_insert = """
                INSERT INTO raw_madrid_air (station_id, data_raw, timestamp)
                VALUES (%s, %s, %s)
            """

            for med in mediciones:
                # Extraemos los campos del XML y los metemos en un diccionario
                # para mantener nuestra estructura dinámica JSONB
                data_dict = {child.tag: child.text for child in med}
                
                # El 'punto_muestreo' en Madrid es 'CodEstacion_CodMagnitud_CodTecnica'
                # Ejemplo: 28079004_8_16 -> La estación es 28079004
                punto_muestreo = data_dict.get('punto_muestreo', '')
                station_id = punto_muestreo.split('_')[0] if punto_muestreo else None
                
                # Construimos el timestamp combinando fecha y hora del XML
                fecha = data_dict.get('fecha', '')
                hora = data_dict.get('hora', '')
                timestamp_str = f"{fecha} {hora}:00"

                cur.execute(query_insert, (
                    station_id,
                    Json(data_dict),
                    timestamp_str
                ))

            connection.commit()
            print("✅ Ingesta de Madrid (XML) completada con éxito.")

        except Exception as e:
            print(f"❌ Error en la ingesta de Madrid: {e}")
            connection.rollback()
            raise
        finally:
            connection.close()
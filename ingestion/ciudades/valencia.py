from database import f_conexion_bd
from utils import f_llamada_api
from psycopg.types.json import Json

def f_run_ingestion_valencia(database_url, api_url):
    connection = f_conexion_bd(database_url, "Valencia_Air_Ingestion")

    with connection.cursor() as cur:
        try:
            response = f_llamada_api(api_url, "Valencia_API")
            data = response.json()
            estaciones = data.get('results', [])

            query_insert = """
                INSERT INTO raw_valencia_air (station_id, data_raw, timestamp)
                VALUES (%s, %s, %s)
            """

            for estacion in estaciones:
                # Envolvemos el dict en Json()
                cur.execute(query_insert, (
                    estacion.get('objectid'),
                    Json(estacion),
                    estacion.get('fecha_carg')
                ))

            connection.commit()
            print(f"✅ Éxito: {len(estaciones)} estaciones enviadas a la BD.")

        except Exception as e:
            print(f"❌ Error en la ingesta de Valencia: {e}")
            connection.rollback()
            raise
        finally:
            connection.close()
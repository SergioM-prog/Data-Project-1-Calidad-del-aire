import os
from sqlalchemy import create_engine

# Obtenemos credenciales de las variables de entorno (las mismas del docker-compose)
user = os.getenv('POSTGRES_USER', 'postgres')
password = os.getenv('POSTGRES_PASSWORD', 'postgres')
db_name = os.getenv('POSTGRES_DB', 'air_quality_db')
host = 'db' # Nombre del servicio en docker-compose
port = '5432'

# URL de conexión
DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"

# Creamos el motor. 
# pool_pre_ping=True ayuda a recuperar la conexión si se corta.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
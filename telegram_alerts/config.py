import os

# Configuración
BOT_TOKEN = os.getenv("BOT_TELEGRAM_TOKEN")
CANAL_ID = os.getenv("ID_CANAL_TELEGRAM")
BARRIER_API_URL = os.getenv("BARRIER_API_URL")
CHECK_INTERVAL = 300  # 5 minutos

PARAMETROS = [
    ("no2", "NO₂", "µg/m³"),
    ("pm10", "PM10", "µg/m³"),
    ("pm25", "PM2.5", "µg/m³"),
    ("so2", "SO₂", "µg/m³"),
    ("o3", "O₃", "µg/m³"),
    ("co", "CO", "mg/m³"),
]
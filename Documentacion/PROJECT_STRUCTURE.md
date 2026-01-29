# Estructura del Proyecto - Data Project Calidad del Aire

Documentación completa de la estructura de archivos y directorios del proyecto.

---

## Árbol de Directorios

```
Data-Project-1-Calidad-del-aire/
│
├── .git/                          # Control de versiones Git
├── .gitignore                     # Archivos ignorados por Git
├── .env                           # Variables de entorno (NO COMMITEAR)
├── .env.example                   # Template de variables de entorno
│
├── docker-compose.yml             # Orquestación de contenedores
│
├── README.md                      # Documentación principal
├── ARCHITECTURE.md                # Arquitectura técnica detallada
├── PROJECT_STRUCTURE.md           # Este archivo
│
├── backend/                       # API Backend (FastAPI)
│   ├── main.py                   # Endpoints y lógica de negocio
│   ├── database.py               # Inicialización de schemas y BD
│   ├── config.py                 # Configuración de conexión
│   ├── requirements.txt          # Dependencias Python
│   └── Dockerfile                # Imagen Docker del backend
│
├── ingestion/                     # Servicio de ingesta de datos
│   ├── main.py                   # Loop principal de ingesta
│   ├── ciudades/                 # Lógica específica por ciudad
│   │   ├── __init__.py
│   │   └── valencia.py           # Ingesta de Valencia API
│   ├── requirements.txt          # Dependencias Python
│   └── Dockerfile                # Imagen Docker de ingestion
│
├── dbt/                           # Transformaciones dbt
│   └── air_quality_dbt/          # Proyecto dbt principal
│       ├── dbt_project.yml       # Configuración del proyecto dbt
│       ├── profiles.yml          # Configuración de conexión a BD
│       ├── packages.yml          # Paquetes dbt externos
│       ├── models/               # Modelos SQL de transformación
│       │   ├── staging/          # Capa Silver - Limpieza
│       │   │   ├── schema.yml
│       │   │   ├── stg_valencia_air.sql
│       │   │   ├── stg_valencia_air_historical_real_daily.sql
│       │   │   └── stg_valencia_air_historical_simulated_hourly.sql
│       │   │
│       │   ├── intermediate/     # Capa Silver - Agregaciones
│       │   │   ├── schema.yml
│       │   │   └── int_air_quality_union_hourly.sql
│       │   │
│       │   └── marts/            # Capa Gold - Fact Tables
│       │       ├── schema.yml
│       │       ├── fct_air_quality_hourly.sql
│       │       ├── fct_air_quality_daily.sql
│       │       ├── fct_alertas_actuales_contaminacion.sql
│       │       ├── fct_limites_de_contaminacion.sql
│       │       ├── fct_dim_estaciones.sql
│       │       ├── fct_calidad_aire_semanal.sql
│       │       ├── fct_ranking_estaciones_contaminadas.sql
│       │       └── fct_air_quality_detailed_analysis.sql
│       │
│       ├── seeds/                # Datos semilla (CSV estáticos)
│       ├── snapshots/            # Snapshots de datos históricos
│       ├── tests/                # Tests de calidad de datos
│       ├── macros/               # Macros SQL reutilizables
│       └── dbt_packages/         # Paquetes instalados (git-ignored)
│
├── telegram_alerts/               # Sistema de alertas por Telegram
│   ├── main.py                   # Loop de verificación de alertas
│   ├── config.py                 # Configuración de Telegram Bot
│   ├── requirements.txt          # Dependencias Python
│   └── Dockerfile                # Imagen Docker de alertas
│
├── grafana/                       # Configuración de Grafana
│   ├── provisioning/             # Configuración automática
│   │   └── datasources/          # Datasources configurados
│   │       └── postgres.yml      # Conexión a PostgreSQL
│   └── dashboards/               # Dashboards preconfigurados
│       └── air_quality.json      # Dashboard principal
│
├── frontend/                      # Dashboard Dash (opcional)
│   ├── app.py                    # Aplicación Dash/Plotly
│   ├── requirements.txt          # Dependencias Python
│   └── Dockerfile                # Imagen Docker frontend
│
├── historical/                    # Datos históricos (CSV)
│   ├── real/                     # Datos reales históricos
│   │   └── *.csv                 # CSVs por año/mes
│   └── simulated/                # Datos simulados para testing
│       └── *.csv                 # CSVs simulados
│
└── scripts/                       # Scripts utilitarios
    ├── generate_api_key.py       # Generador de API keys
    └── setup_database.sh         # Script de inicialización (opcional)
```

---

## Descripción Detallada de Archivos

### Raíz del Proyecto

#### `docker-compose.yml`

**Propósito:** Orquestación de todos los servicios del proyecto.

**Servicios definidos:**
- `db` - PostgreSQL 17
- `backend` - FastAPI Barrier API
- `ingestion-valencia` - Servicio de ingesta
- `dbt` - Transformaciones SQL
- `telegram-alerts` - Sistema de alertas
- `grafana` - Visualización
- `frontend` - Dashboard Dash (comentado)

**Configuraciones clave:**
```yaml
services:
  db:
    image: postgres:17-alpine
    ports: ["5431:5432"]
    volumes: [postgres_data:/var/lib/postgresql/data]

  backend:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [db]
    healthcheck: [curl, http://localhost:8000/health]
```

#### `.env`

**Propósito:** Variables de entorno sensibles (NO COMMITEAR).

**Variables requeridas:**
```env
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<password>
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=air_quality_db

# API Keys
INGESTION_VALENCIA_API_KEY=sk_xxx
TELEGRAM_ALERTS_API_KEY=sk_xxx
BARRIER_API_URL=http://backend:8000

# Telegram
BOT_TELEGRAM_TOKEN=123456:ABC...
ID_CANAL_TELEGRAM=-1001234567890

# Grafana
GF_SECURITY_ADMIN_PASSWORD=<password>
```

**⚠️ IMPORTANTE:** Este archivo DEBE estar en `.gitignore`.

#### `.gitignore`

**Propósito:** Archivos y directorios a ignorar por Git.

**Incluye:**
```
.env
__pycache__/
*.pyc
dbt/air_quality_dbt/dbt_packages/
dbt/air_quality_dbt/logs/
dbt/air_quality_dbt/target/
.DS_Store
```

---

### `/backend` - API Backend (FastAPI)

#### `backend/main.py` (500+ líneas)

**Propósito:** Implementación del Barrier API Pattern.

**Responsabilidades:**
1. Autenticación M2M con API keys
2. Endpoints para ingesta de datos
3. Endpoints para consulta de alertas
4. Health checks

**Endpoints implementados:**

```python
@app.post("/api/ingest")
async def ingest_data(
    datos: list[AirQualityInbound],
    x_api_key: str = Depends(verify_api_key)
):
    # Recibe datos, valida, deduplica, inserta en raw

@app.get("/api/alertas")
async def get_alertas(
    x_api_key: str = Depends(verify_api_key)
):
    # Retorna alertas desde fct_alertas_actuales_contaminacion

@app.post("/api/alertas/registrar-envio")
async def registrar_alerta_enviada(
    alertas: list[AlertaEnviadaInbound],
    x_api_key: str = Depends(verify_api_key)
):
    # Registra alertas enviadas para evitar duplicados

@app.get("/health")
async def health_check():
    # Health check para Docker
```

**Modelos Pydantic:**
```python
class AirQualityInbound(BaseModel):
    objectid: int
    nombre: str
    fecha_carg: str
    so2: Optional[float] = None
    no2: Optional[float] = None
    # ... otros contaminantes

    model_config = ConfigDict(extra='forbid')
```

**Líneas críticas:**
- `93-114`: Autenticación M2M
- `150-185`: Ingesta con deduplicación
- `193-216`: Consulta de alertas

#### `backend/database.py` (400+ líneas)

**Propósito:** Inicialización de schemas y carga de datos históricos.

**Funciones principales:**

```python
def initialize_database():
    # Crea schemas: raw, staging, intermediate, marts, alerts, security

def create_raw_tables(engine):
    # Crea tablas raw para datos de Valencia

def create_security_tables(engine):
    # Crea tabla de API keys

def load_historical_data(engine):
    # Carga CSVs históricos en raw tables
```

**Schemas creados:**
1. `raw` - Datos sin procesar
2. `staging` - (creado por dbt como views)
3. `intermediate` - (creado por dbt como tables)
4. `marts` - (creado por dbt como tables)
5. `alerts` - Historial de alertas
6. `security` - API keys

**Líneas críticas:**
- `281`: Riesgo de SQL injection (f-string)
- `303-398`: Carga de CSVs sin validación

#### `backend/config.py` (20 líneas)

**Propósito:** Configuración de conexión a PostgreSQL.

```python
import os
from sqlalchemy import create_engine

DATABASE_URL = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
```

#### `backend/requirements.txt`

**Dependencias:**
```
fastapi
uvicorn[standard]
pandas
sqlalchemy
psycopg[binary]
pydantic
python-dotenv
```

---

### `/ingestion` - Servicio de Ingesta

#### `ingestion/main.py` (50 líneas)

**Propósito:** Loop principal de ingesta cada 30 minutos.

```python
INTERVAL_SECONDS = 1800  # 30 minutos

while True:
    try:
        datos = obtener_datos_valencia_api()
        enviar_a_backend(datos)
        print(f"Ingesta exitosa: {len(datos)} registros")
    except Exception as e:
        print(f"Error en ingesta: {e}")

    time.sleep(INTERVAL_SECONDS)
```

**Líneas críticas:**
- `17`: Intervalo hardcodeado (debería ser env var)

#### `ingestion/ciudades/valencia.py` (100 líneas)

**Propósito:** Lógica específica para Valencia OpenDataSoft API.

**Funciones:**

```python
def obtener_datos_valencia_api():
    url = "https://valencia.opendatasoft.com/api/v2/catalog/datasets/..."
    response = requests.get(url, timeout=30)
    records = [record["fields"] for record in response.json()["records"]]
    return records

def enviar_a_backend(datos):
    validated = [AirQualityInbound(**record) for record in datos]
    response = requests.post(
        f"{BARRIER_API_URL}/api/ingest",
        headers={"X-API-Key": API_KEY},
        json=[d.model_dump() for d in validated]
    )
```

---

### `/dbt` - Transformaciones SQL

#### `dbt/air_quality_dbt/dbt_project.yml`

**Propósito:** Configuración del proyecto dbt.

```yaml
name: 'air_quality_dbt'
version: '1.0.0'
profile: 'air_quality_dbt'

models:
  air_quality_dbt:
    staging:
      +materialized: view
    intermediate:
      +materialized: table
    marts:
      +materialized: table
```

#### `dbt/air_quality_dbt/profiles.yml`

**Propósito:** Configuración de conexión a PostgreSQL.

**⚠️ PROBLEMA:** Credenciales hardcodeadas (líneas 4-6).

```yaml
air_quality_dbt:
  target: dev
  outputs:
    dev:
      type: postgres
      user: postgres           # ❌ Hardcoded
      password: postgres       # ❌ Hardcoded
      dbname: air_quality_db   # ❌ Hardcoded
      host: db
      port: 5432
```

**Solución:**
```yaml
user: "{{ env_var('POSTGRES_USER') }}"
password: "{{ env_var('POSTGRES_PASSWORD') }}"
```

#### Modelos dbt

##### `models/staging/stg_valencia_air.sql`

**Materialización:** View
**Propósito:** Limpieza y tipado de datos raw.

```sql
SELECT
    objectid,
    nombre,
    CAST(fecha_carg AS TIMESTAMP) AS fecha_hora,
    CAST(so2 AS FLOAT) AS so2,
    CAST(no2 AS FLOAT) AS no2,
    -- ... otros campos
FROM {{ source('raw', 'valencia_air_real_hourly') }}
WHERE fecha_carg IS NOT NULL
```

##### `models/intermediate/int_air_quality_union_hourly.sql`

**Materialización:** Table
**Propósito:** Unión de real + histórico + simulado con deduplicación.

```sql
WITH real_data AS (
    SELECT * FROM {{ ref('stg_valencia_air') }}
),
historical_data AS (
    SELECT * FROM {{ ref('stg_valencia_air_historical_real_daily') }}
),
simulated_data AS (
    SELECT * FROM {{ ref('stg_valencia_air_historical_simulated_hourly') }}
),
unioned AS (
    SELECT * FROM real_data
    UNION ALL
    SELECT * FROM historical_data
    UNION ALL
    SELECT * FROM simulated_data
),
deduplicated AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY objectid, fecha_hora
               ORDER BY fecha_carg DESC
           ) AS row_num
    FROM unioned
)
SELECT * FROM deduplicated WHERE row_num = 1
```

##### `models/marts/fct_alertas_actuales_contaminacion.sql`

**Materialización:** Table
**Propósito:** Identificar alertas activas (valor > percentil 75).

```sql
WITH mediciones_recientes AS (
    SELECT * FROM {{ ref('fct_air_quality_hourly') }}
    WHERE fecha_hora >= NOW() - INTERVAL '2 hours'
),
limites AS (
    SELECT * FROM {{ ref('fct_limites_de_contaminacion') }}
)
SELECT
    m.objectid AS id_estacion,
    m.nombre AS nombre_estacion,
    m.fecha_hora AS fecha_hora_alerta,
    m.parametro,
    m.valor_medido,
    l.limite_p75,
    m.valor_medido - l.limite_p75 AS exceso
FROM mediciones_recientes m
JOIN limites l
    ON m.parametro = l.parametro
    AND EXTRACT(HOUR FROM m.fecha_hora) = l.hora_del_dia
WHERE m.valor_medido > l.limite_p75
```

---

### `/telegram_alerts` - Sistema de Alertas

#### `telegram_alerts/main.py` (150 líneas)

**Propósito:** Loop de verificación y envío de alertas cada 5 minutos.

**Proceso:**

```python
CHECK_INTERVAL = 300  # 5 minutos

while True:
    # 1. Obtener alertas desde backend
    alertas = requests.get(
        f"{BARRIER_API_URL}/api/alertas",
        headers={"X-API-Key": API_KEY}
    ).json()

    # 2. Para cada alerta
    for alerta in alertas:
        # 3. Formatear mensaje
        mensaje = formatear_mensaje_alerta(alerta)

        # 4. Enviar a Telegram
        enviar_mensaje_telegram(mensaje)

        # 5. Registrar como enviada
        registrar_alerta_enviada(alerta)

    time.sleep(CHECK_INTERVAL)
```

**Formato de mensaje:**

```python
def formatear_mensaje_alerta(alerta):
    return f"""
🚨 *ALERTA DE CONTAMINACIÓN* 🚨

📍 *Estación:* {alerta['nombre_estacion']}
🕒 *Fecha/Hora:* {alerta['fecha_hora_alerta']}
🧪 *Contaminante:* {alerta['parametro']}
📊 *Valor Medido:* {alerta['valor_medido']:.2f}
⚠️ *Límite P75:* {alerta['limite_p75']:.2f}
📈 *Exceso:* {alerta['exceso']:.2f}
"""
```

**Líneas críticas:**
- `75-80`: Sin sanitización de input (riesgo de inyección de markdown)

#### `telegram_alerts/config.py`

**Propósito:** Configuración del bot.

```python
import os

BOT_TOKEN = os.getenv("BOT_TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("ID_CANAL_TELEGRAM")
API_KEY = os.getenv("TELEGRAM_ALERTS_API_KEY")
BARRIER_API_URL = os.getenv("BARRIER_API_URL")
CHECK_INTERVAL = 300  # 5 minutos
```

---

### `/grafana` - Visualización

#### `grafana/provisioning/datasources/postgres.yml`

**Propósito:** Auto-configuración del datasource PostgreSQL.

```yaml
apiVersion: 1

datasources:
  - name: PostgreSQL
    type: postgres
    access: proxy
    url: db:5432
    database: air_quality_db
    user: ${POSTGRES_USER}
    jsonData:
      sslmode: disable
      postgresVersion: 1700
    secureJsonData:
      password: ${POSTGRES_PASSWORD}
```

#### `grafana/dashboards/`

**Propósito:** Dashboards preconfigurados.

**Dashboards típicos:**
- Calidad del aire en tiempo real
- Histórico de contaminantes
- Alertas enviadas
- Comparativa de estaciones

---

### `/historical` - Datos Históricos

#### `historical/real/`

**Contenido:** CSVs con datos reales históricos (2014-2025).

**Formato:**
```csv
objectid,fecha,so2,no2,o3,co,pm10,pm25
1,2024-01-01,5.2,23.1,45.3,0.3,15.2,8.1
```

**Carga:** Se cargan automáticamente en `raw.valencia_air_historical_real_daily` al iniciar el backend.

#### `historical/simulated/`

**Contenido:** CSVs con datos simulados (2025-2026) para testing.

**Propósito:** Backtesting y proyecciones.

---

### `/scripts` - Utilidades

#### `scripts/generate_api_key.py`

**Propósito:** Generar API keys para servicios M2M.

**Uso:**
```bash
python scripts/generate_api_key.py
```

**Output:**
```
Generando API keys para servicios...
INGESTION_VALENCIA_API_KEY=sk_1a2b3c4d5e6f...
TELEGRAM_ALERTS_API_KEY=sk_7g8h9i0j1k2l...

Agregar estas claves al archivo .env
```

---

## Flujo de Datos Entre Archivos

```
┌─────────────────────────────────────────────────────────────┐
│                    FLUJO DE EJECUCIÓN                       │
└─────────────────────────────────────────────────────────────┘

1. INICIO DEL SISTEMA
   docker-compose.yml
   └─> Levanta servicios en orden:
       1. db (PostgreSQL)
       2. backend (espera db healthy)
       3. ingestion-valencia (espera backend healthy)
       4. dbt (loop cada 5 min)
       5. telegram-alerts (espera backend healthy)
       6. grafana

2. INGESTION LOOP
   ingestion/main.py
   └─> ingestion/ciudades/valencia.py
       └─> obtener_datos_valencia_api()
           └─> POST backend/main.py::/api/ingest
               └─> backend/database.py::raw tables

3. DBT TRANSFORMATIONS
   dbt run (cada 5 min)
   └─> models/staging/*.sql (views)
       └─> models/intermediate/*.sql (tables)
           └─> models/marts/*.sql (fact tables)

4. ALERTAS
   telegram_alerts/main.py
   └─> GET backend/main.py::/api/alertas
       └─> Query marts.fct_alertas_actuales_contaminacion
           └─> POST Telegram API
               └─> POST backend/main.py::/api/alertas/registrar-envio
                   └─> INSERT alerts.alertas_enviadas_telegram

5. VISUALIZACIÓN
   Grafana
   └─> Query PostgreSQL:marts.*
       └─> Render dashboards
```

---

## Archivos Críticos (Orden de Importancia)

### Alta Criticidad

1. **`backend/main.py`** - Core API, sin esto nada funciona
2. **`docker-compose.yml`** - Orquestación, define toda la arquitectura
3. **`.env`** - Credenciales, sin esto servicios no arrancan
4. **`dbt/air_quality_dbt/models/marts/*.sql`** - Tablas finales de datos

### Media Criticidad

5. **`ingestion/ciudades/valencia.py`** - Ingesta de datos, pero puede fallar temporalmente
6. **`telegram_alerts/main.py`** - Alertas, pero no bloquea el sistema
7. **`backend/database.py`** - Inicialización, se ejecuta una vez

### Baja Criticidad

8. **`grafana/dashboards/`** - Visualización, se puede recrear
9. **`historical/`** - Datos históricos, útiles pero no críticos para operación
10. **`scripts/generate_api_key.py`** - Utilidad de setup

---

## Tamaño de Archivos (Aproximado)

| Archivo/Directorio | Tamaño | Líneas de Código |
|-------------------|--------|------------------|
| `backend/main.py` | 20 KB | ~500 LOC |
| `backend/database.py` | 15 KB | ~400 LOC |
| `dbt/models/` | 50 KB | ~1500 LOC SQL |
| `historical/` | 500 MB | N/A (CSV data) |
| `ingestion/` | 5 KB | ~150 LOC |
| `telegram_alerts/` | 6 KB | ~180 LOC |

---

## Convenciones de Código

### Python

- **Formato:** PEP 8
- **Imports:** stdlib → third-party → local
- **Type hints:** Parcial (Pydantic models sí, funciones no siempre)
- **Docstrings:** Limitados (mejorable)

### SQL (dbt)

- **Naming:** `snake_case`
- **Prefijos:** `stg_` (staging), `int_` (intermediate), `fct_` (fact)
- **CTEs:** Preferidos sobre subqueries
- **Formato:** Indentación 4 espacios

### Docker

- **Base images:** Alpine cuando sea posible
- **Multi-stage builds:** No usado (oportunidad de mejora)
- **Health checks:** Implementados en servicios críticos

---

## Archivos que NO Existen (Pero Deberían)

### Tests

```
tests/
├── test_backend_api.py
├── test_ingestion.py
├── test_pydantic_models.py
└── conftest.py
```

### Configuración CI/CD

```
.github/
└── workflows/
    ├── tests.yml
    ├── build.yml
    └── deploy.yml
```

### Documentación Adicional

```
docs/
├── API.md              # Documentación de endpoints
├── DATA_DICTIONARY.md  # Diccionario de datos
└── DEPLOYMENT.md       # Guía de deployment
```

---

## Referencias Cruzadas

- Ver [README.md](README.md) para guía de inicio rápido
- Ver [ARCHITECTURE.md](ARCHITECTURE.md) para análisis técnico profundo
- Ver `.gitignore` para archivos no rastreados

---

**Última actualización:** 2026-01-29
**Versión:** 1.0

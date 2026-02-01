# Sistema de Monitoreo de Calidad del Aire - Valencia

Pipeline completo de datos para ingesta, transformación y análisis de calidad del aire en tiempo real.

[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue)](https://www.postgresql.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)](https://fastapi.tiangolo.com/)
[![dbt](https://img.shields.io/badge/dbt-1.8.2-orange)](https://www.getdbt.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue)](https://www.docker.com/)

## Inicio Rápido

### Prerrequisitos

```bash
# Verificar instalaciones
docker --version          # Docker 20.10+
docker-compose --version  # Docker Compose 2.0+
python --version          # Python 3.10+ (para scripts)
```

### Instalación en 5 Pasos

#### 1. Clonar el Repositorio

```bash
git clone https://github.com/tu-usuario/Data-Project-1-Calidad-del-aire.git
cd Data-Project-1-Calidad-del-aire
```

#### 2. Configurar Variables de Entorno

```bash
# Copiar template
cp .env.example .env  # Si existe, sino crear manualmente

# Editar .env con tus credenciales
nano .env


#### 3. Generar API Keys

```bash
python scripts/generate_api_key.py
```

Esto creará claves para autenticación M2M. Copia las claves generadas al archivo `.env`.

#### 4. Levantar los Servicios

```bash
docker-compose up -d
```

**Servicios que se iniciarán:**

```
✓ PostgreSQL (puerto 5431)
✓ Backend API (puerto 8000)
✓ Ingestion Service (background)
✓ dbt Transformations (background)
✓ Telegram Alerts (background)
✓ Grafana (puerto 3000)
```

#### 5. Verificar Estado

```bash
# Ver estado de contenedores
docker-compose ps

# Ver logs
docker-compose logs -f backend

# Health check del backend
curl http://localhost:8000/health
```

**Respuesta esperada:**

```json
{"status": "healthy"}
```

## Acceso a Servicios

| Servicio | URL | Credenciales |
|----------|-----|--------------|
| **Grafana** | http://localhost:3000 | admin / (password del .env) |
| **Backend API** | http://localhost:8000 | API Key en header |
| **API Docs** | http://localhost:8000/docs | Swagger UI automático |
| **PostgreSQL** | localhost:5431 | user/pass del .env |

## Arquitectura Resumida

```
┌─────────────────────────────────────────────────────────────┐
│  Valencia OpenDataSoft API (Datos públicos cada 30 min)    │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
          ┌──────────────────────┐
          │  Ingestion Service   │  ← Python + Pydantic
          │   (cada 30 min)      │
          └──────────┬───────────┘
                     │ POST /api/ingest + API Key
                     ▼
          ┌──────────────────────┐
          │   Backend API        │  ← FastAPI (puerto 8000)
          │  (Barrier Pattern)   │
          └──────────┬───────────┘
                     │ INSERT con deduplicación
                     ▼
    ┌────────────────────────────────────────┐
    │      PostgreSQL 17 (puerto 5431)       │
    │  ┌──────────────────────────────────┐  │
    │  │  raw → staging → intermediate    │  │
    │  │           → marts                │  │  ← dbt (cada 5 min)
    │  └──────────────────────────────────┘  │
    └────┬───────────────────┬────────────────┘
         │                   │
         ▼                   ▼
    ┌─────────┐      ┌──────────────┐
    │ Grafana │      │   Telegram   │
    │ (port   │      │    Alerts    │
    │  3000)  │      │  (cada 5min) │
    └─────────┘      └──────────────┘
```

## Uso Básico

### Consultar Datos via API

```bash
# Obtener alertas actuales
curl -X GET http://localhost:8000/api/alertas \
  -H "X-API-Key: tu_api_key_aqui"

# Ingestar datos manualmente (para testing)
curl -X POST http://localhost:8000/api/ingest \
  -H "X-API-Key: tu_api_key_aqui" \
  -H "Content-Type: application/json" \
  -d @ejemplo_payload.json
```

### Conectarse a PostgreSQL

```bash
# Con psql
psql -h localhost -p 5431 -U postgres -d air_quality_db

# O con cualquier cliente SQL (DBeaver, pgAdmin, etc.)
```

**Consultas útiles:**

```sql
-- Ver últimas mediciones
SELECT * FROM raw.valencia_air_real_hourly
ORDER BY fecha_carg DESC
LIMIT 10;

-- Ver alertas actuales
SELECT * FROM marts.fct_alertas_actuales_contaminacion;

-- Ver estaciones
SELECT * FROM marts.fct_dim_estaciones;
```

### Ver Dashboards en Grafana

1. Ir a http://localhost:3000
2. Login con `admin` / tu password
3. Navegar a **Dashboards** → Dashboards preconfigurados

## Estructura del Proyecto

```
Data-Project-1-Calidad-del-aire/
├── backend/              # FastAPI barrier API
│   ├── main.py          # Endpoints y lógica principal
│   ├── database.py      # Schema y conexiones
│   ├── config.py        # Configuración DB
│   └── requirements.txt
│
├── ingestion/           # Servicio de ingesta
│   ├── main.py          # Loop principal
│   ├── ciudades/
│   │   └── valencia.py  # Lógica específica Valencia
│   └── requirements.txt
│
├── dbt/                 # Transformaciones SQL
│   └── air_quality_dbt/
│       ├── models/      # Modelos SQL (staging, marts)
│       └── profiles.yml # Configuración dbt
│
├── telegram_alerts/     # Sistema de alertas
│   ├── main.py
│   ├── config.py
│   └── requirements.txt
│
├── grafana/             # Configuración Grafana
│   ├── provisioning/
│   └── dashboards/
│
├── historical/          # Datos históricos CSV
│   ├── real/
│   └── simulated/
│
├── scripts/             # Utilidades
│   └── generate_api_key.py
│
├── docker-compose.yml   # Orquestación
├── .env                 # Variables de entorno (no commitear)
├── .gitignore
└── README.md
```

Ver [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) para detalles completos.

## Datos Monitoreados

### Contaminantes

| Código | Nombre | Descripción |
|--------|--------|-------------|
| **SO2** | Dióxido de Azufre | Gas tóxico de combustión |
| **NO2** | Dióxido de Nitrógeno | Contaminante del tráfico |
| **O3** | Ozono | Oxidante fotoquímico |
| **CO** | Monóxido de Carbono | Gas de combustión incompleta |
| **PM10** | Partículas 10µm | Polvo y aerosoles |
| **PM2.5** | Partículas 2.5µm | Partículas finas respirables |

### Estaciones (11 en Valencia)

Dr. Lluch • Francia • Boulevar Sur • Molí del Sol • Pista de Silla • Universidad Politécnica • Viveros • Centro • Cabanyal • Olivereta • Patraix

## Gestión del Sistema

### Comandos Útiles

```bash
# Ver logs en tiempo real
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f backend
docker-compose logs -f ingestion-valencia
docker-compose logs -f telegram-alerts

# Reiniciar un servicio
docker-compose restart backend

# Detener todo
docker-compose down

# Detener y eliminar volúmenes (CUIDADO: borra la BD)
docker-compose down -v

# Reconstruir imágenes
docker-compose build --no-cache

# Ejecutar dbt manualmente
docker-compose exec dbt dbt run
docker-compose exec dbt dbt test
```

### Troubleshooting

#### Backend no arranca

```bash
# Ver logs detallados
docker-compose logs backend

# Verificar que PostgreSQL esté corriendo
docker-compose ps db

# Reiniciar backend
docker-compose restart backend
```

#### Ingestion falla

```bash
# Verificar API key en .env
echo $INGESTION_VALENCIA_API_KEY

# Verificar conectividad con backend
docker-compose exec ingestion-valencia curl http://backend:8000/health

# Ver logs de ingestion
docker-compose logs -f ingestion-valencia
```

#### dbt no transforma datos

```bash
# Verificar logs dbt
docker-compose logs dbt

# Ejecutar manualmente para ver errores
docker-compose exec dbt dbt run --profiles-dir .

# Ver qué modelos fallaron
docker-compose exec dbt dbt test
```

#### PostgreSQL no acepta conexiones

```bash
# Verificar que el contenedor esté running
docker-compose ps db

# Verificar puerto
netstat -an | grep 5431

# Conectarse desde el host
psql -h localhost -p 5431 -U postgres -d air_quality_db
```

## Desarrollo

### Agregar Nueva Ciudad

1. Crear archivo en `ingestion/ciudades/nueva_ciudad.py`
2. Implementar función `obtener_datos_nueva_ciudad_api()`
3. Agregar servicio en `docker-compose.yml`
4. Crear tabla raw en `backend/database.py`

### Agregar Nuevo Modelo dbt

1. Crear SQL en `dbt/air_quality_dbt/models/marts/`
2. Agregar documentación en `schema.yml`
3. Ejecutar `dbt run` para materializar
4. Verificar con `dbt test`

### Contribuir

1. Fork del repositorio
2. Crear rama: `git checkout -b feature/nueva-funcionalidad`
3. Commit: `git commit -m 'Add: nueva funcionalidad'`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Abrir Pull Request

## Issues Conocidos

⚠️ **Issues Críticos Identificados** - Ver [ARCHITECTURE.md](ARCHITECTURE.md#problemas-identificados)

1. Endpoint `/api/v1/hourly-metrics` no implementado (frontend roto)
2. Credenciales hardcodeadas en `dbt/air_quality_dbt/profiles.yml`
3. Sin HTTPS (API keys sin cifrar)
4. Password default de Grafana hardcodeado

## Documentación Técnica

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Arquitectura detallada, análisis de seguridad, problemas identificados
- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Estructura completa del proyecto, descripción de cada archivo

## Stack Tecnológico

| Componente | Tecnología | Versión |
|------------|------------|---------|
| Base de Datos | PostgreSQL | 17 Alpine |
| Backend API | FastAPI | Latest |
| ORM | SQLAlchemy | Latest |
| Validación | Pydantic | v2 |
| ETL | dbt | 1.8.2 |
| Orquestación | Docker Compose | 2.0+ |
| Visualización | Grafana | Latest |
| Alertas | Telegram Bot API | Latest |


## Referencias

- [Valencia OpenDataSoft API](https://valencia.opendatasoft.com/)
- [dbt Documentation](https://docs.getdbt.com/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [PostgreSQL Docs](https://www.postgresql.org/docs/17/)

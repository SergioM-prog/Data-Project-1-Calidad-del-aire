# DOCUMENTACIÓN TÉCNICA DEL PROYECTO

## Pipeline de Datos de Calidad del Aire

---

## 1. INTRODUCCIÓN

Este documento describe la arquitectura y funcionamiento de un pipeline de datos diseñado para recopilar, transformar y visualizar información sobre la calidad del aire en diversas ciudades españolas. El proyecto implementa una arquitectura de datos moderna siguiendo el patrón Medallion, utilizando tecnologías open-source como Docker, PostgreSQL, dbt y Grafana.

Este pipeline automatiza el proceso completo desde la extracción de datos de APIs públicas hasta la presentación de métricas agregadas en dashboards interactivos, pasando por múltiples capas de transformación y limpieza de datos.

---

## 2. ARQUITECTURA GENERAL DEL SISTEMA

El sistema sigue un flujo de datos secuencial que comienza con la extracción de información desde APIs públicas y finaliza con la visualización de métricas agregadas:

```
APIs Públicas → Aplicación Python → PostgreSQL → dbt → Grafana
```

La arquitectura implementa el patrón Medallion con cuatro capas claramente diferenciadas:

- **Raw**: Almacenamiento de datos crudos sin procesar, tal como llegan desde las APIs externas
- **Staging**: Primera capa de limpieza donde se extraen y tipifican los campos del JSON
- **Intermediate**: Unificación de múltiples fuentes de datos en una estructura común
- **Marts**: Tablas analíticas agregadas y optimizadas para consultas de negocio

---

## 3. COMPONENTES DEL SISTEMA

### 3.1 Base de Datos PostgreSQL

**Ubicación en docker-compose**: Líneas 2-8

La base de datos PostgreSQL actúa como repositorio central de información para todo el pipeline. Se utiliza la versión 17-alpine, que es una distribución ligera basada en Alpine Linux que reduce el tamaño de la imagen Docker manteniendo toda la funcionalidad necesaria.

**Configuración del servicio**:
- Imagen: postgres:17-alpine
- Puerto expuesto: 5431 (puerto del host que mapea al puerto interno 5432 del contenedor)
- Base de datos: air_quality_db
- Usuario: postgres
- Contraseña: postgres (definida en archivo .env para facilitar cambios sin modificar código)

**Razón del puerto 5431**: Se utiliza un puerto diferente al estándar (5432) para evitar conflictos si el desarrollador tiene otra instancia de PostgreSQL corriendo localmente en su máquina.

**Estructura de esquemas**:

La base de datos se organiza en cuatro esquemas según la arquitectura Medallion. Esta separación permite un procesamiento en capas donde cada nivel tiene una responsabilidad específica:

1. **raw**: Contiene las tablas con datos crudos en formato JSONB tal como llegan desde las APIs. No se aplica ninguna transformación, lo que garantiza que siempre tengamos acceso a los datos originales para auditoría o reprocesamiento. Actualmente incluye:
   - `raw.valencia_air`: Datos de estaciones de Valencia
   - `raw.madrid_air`: Datos de estaciones de Madrid (inactiva actualmente)

2. **staging**: Almacena vistas SQL que extraen campos específicos del JSONB y los tipifican correctamente (FLOAT para números, TIMESTAMP para fechas, TEXT para cadenas). Las vistas no duplican datos, solo proporcionan una forma estructurada de acceder a ellos.

3. **intermediate**: Contiene tablas físicas que unifican datos de múltiples ciudades en una estructura común. Esta capa añade la columna `city` para identificar el origen de cada registro y normaliza los nombres de campos entre diferentes fuentes.

4. **marts**: Tablas analíticas agregadas por diferentes dimensiones temporales (diario, horario). Estas tablas están optimizadas para consultas de negocio, calculando promedios, máximos y otras métricas relevantes.

---

### 3.2 Aplicación de Ingestión (Python)

**Ubicación**: Directorio `app/`
**Configuración en docker-compose**: Líneas 10-20

La aplicación de ingestión es el primer componente del pipeline. Su responsabilidad es extraer datos desde las APIs públicas gubernamentales e insertarlos en la capa raw de la base de datos sin aplicar ninguna transformación. Está construida en Python 3 y organizada en módulos especializados siguiendo el principio de separación de responsabilidades.

**Tecnologías utilizadas**:
- `psycopg`: Librería moderna de PostgreSQL para Python (versión 3)
- `requests`: Para realizar peticiones HTTP a las APIs
- `xml.etree.ElementTree`: Para parsear respuestas XML de la API de Madrid

#### 3.2.1 Módulo config.py

Este archivo centraliza toda la configuración del sistema en un único punto, lo que facilita el mantenimiento y la migración entre entornos (desarrollo, staging, producción).

**Responsabilidades principales**:
- Lectura de variables de entorno desde el archivo `.env` usando `os.getenv()`
- Construcción de la cadena de conexión a PostgreSQL con formato URI
- Definición del diccionario `CITIES_CONFIG` que actúa como registro de ciudades disponibles

**Estructura del diccionario CITIES_CONFIG**:

Cada ciudad tiene tres propiedades obligatorias:
- `api_url`: URL completa de la API pública de la ciudad
- `table_name`: Nombre de la tabla en el esquema raw donde se almacenarán los datos
- `active`: Booleano que controla si la ciudad se procesa en esta ejecución

**Estado actual de ciudades**:
- **Valencia**: Activa (`active: True`) - Se está ingiriendo datos actualmente
- **Madrid**: Inactiva (`active: False`) - Implementada pero desactivada temporalmente
- **País Vasco**: Inactiva (`active: False`) - Estructura definida, pendiente de implementación

Esta arquitectura permite activar o desactivar ciudades cambiando un solo valor, sin necesidad de modificar código.

#### 3.2.2 Módulo database.py

Encapsula toda la lógica relacionada con la base de datos, proporcionando funciones reutilizables para conexión y creación de infraestructura.

**Función f_conexion_bd(db_url, db_nombre)**:

Esta función establece una conexión robusta a PostgreSQL con manejo de errores.

- Recibe la URL de conexión y un nombre descriptivo para logging
- Implementa lógica de reintentos: 10 intentos con pausas de 2 segundos entre cada uno
- Esto es crucial en Docker, donde PostgreSQL puede tardar varios segundos en estar completamente listo
- Retorna un objeto de conexión si tiene éxito
- Lanza una excepción `RuntimeError` si falla tras todos los intentos

**Función f_crear_tablas(database_url)**:

Esta función asegura que la infraestructura de base de datos exista antes de comenzar la ingesta.

- Se ejecuta al inicio de cada ejecución del orquestador
- Crea los cuatro esquemas (raw, staging, intermediate, marts) si no existen usando `CREATE SCHEMA IF NOT EXISTS`
- Crea las tablas raw para cada ciudad con la estructura estándar:
  - `id`: Clave primaria autoincrementable (SERIAL)
  - `station_id`: Identificador de la estación de medición (INTEGER)
  - `data_raw`: Campo JSONB que almacena el payload completo de la API sin modificar
  - `timestamp`: Marca temporal de la medición (TIMESTAMP WITH TIME ZONE)

El uso de `IF NOT EXISTS` hace que la función sea idempotente: se puede ejecutar múltiples veces sin causar errores.

#### 3.2.3 Módulo utils.py

Contiene funciones auxiliares reutilizables que se usan en múltiples partes del proyecto.

**Función f_llamada_api(api_url, api_nombre)**:

Esta función encapsula la lógica de llamadas HTTP con manejo robusto de errores.

- Realiza peticiones HTTP GET a las APIs públicas
- Implementa reintentos automáticos: 10 intentos con pausas de 2 segundos
- Esto hace el sistema resiliente ante caídas temporales de las APIs externas o problemas de red
- Captura excepciones de tipo `requests.exceptions.RequestException` que incluyen timeouts, errores de conexión, etc.
- Registra cada intento fallido en consola para facilitar el debugging
- Retorna el objeto `response` de la librería requests, que contiene status code, headers y contenido
- Lanza `RuntimeError` si todos los intentos fallan

Esta función es crítica porque las APIs externas pueden tener intermitencias, especialmente las gubernamentales que no están diseñadas para alta disponibilidad.

#### 3.2.4 Módulo main.py (Orquestador)

Este es el punto de entrada principal de la aplicación. Contiene la función `orquestador()` que coordina todo el proceso de ingestión de forma secuencial y controlada.

**Diccionario INGESTION_MAP**:

Mapea nombres de ciudades con sus funciones específicas de ingestión. Este patrón de diseño permite añadir nuevas ciudades simplemente registrando su función aquí:
```python
INGESTION_MAP = {
    "valencia": f_run_ingestion_valencia,
    "madrid": f_run_ingestion_madrid,
}
```

**Flujo de ejecución detallado**:

1. **Espera inicial (5 segundos)**:
   - Pausa deliberada para asegurar que PostgreSQL ha arrancado completamente en Docker
   - En Docker Compose, aunque `depends_on` establece orden de inicio, no garantiza que el servicio esté listo para aceptar conexiones
   - Esta espera evita errores de conexión en el primer intento

2. **Verificación de infraestructura**:
   - Llama a `f_crear_tablas()` para crear esquemas y tablas si no existen
   - Si esta etapa falla, se detiene toda la ejecución con `return` porque no tiene sentido continuar sin base de datos

3. **Iteración sobre ciudades configuradas**:
   - Recorre el diccionario `CITIES_CONFIG` obtenido desde config.py
   - Para cada ciudad, verifica la propiedad `active`
   - Solo procesa ciudades con `active: True`, saltando las demás

4. **Resolución de función mediante mapeo**:
   - Busca la función correspondiente en `INGESTION_MAP` usando el nombre de la ciudad como clave
   - Si no encuentra la función, registra un error pero continúa con la siguiente ciudad
   - Este diseño permite tener ciudades configuradas aunque aún no tengan implementación

5. **Ejecución de ingesta específica**:
   - Ejecuta la función de ingesta pasando `DATABASE_URL` y la `api_url` de la ciudad
   - La función se ejecuta dentro de un bloque try-except

6. **Manejo de errores resiliente**:
   - Si una ciudad falla, captura la excepción, registra el error en logs pero continúa con las siguientes
   - Esto evita que un problema en una ciudad detenga la ingesta de las demás
   - Implementa el principio de "fail gracefully"

#### 3.2.5 Módulo ingestion/valencia.py

Implementa la lógica específica para extraer datos de la API de Valencia que proporciona información sobre estaciones de contaminación atmosférica.

**Formato de la API**: La API de Valencia retorna JSON con la siguiente estructura:
```json
{
  "results": [
    {
      "objectid": 123,
      "nombre": "Nombre de la estación",
      "no2": 25.5,
      "pm10": 30.2,
      "fecha_carg": "2024-01-19T10:30:00Z",
      ...otros campos...
    }
  ]
}
```

**Proceso de ingesta paso a paso**:

1. **Conexión a base de datos**: Establece conexión usando `f_conexion_bd()`

2. **Llamada a la API**: Realiza petición GET a través de `f_llamada_api()`

3. **Parsing de respuesta**: Convierte la respuesta HTTP a diccionario Python con `.json()`

4. **Extracción del array de estaciones**: Obtiene la lista de estaciones desde `data.get('results', [])`

5. **Inserción iterativa**: Para cada estación en el array:
   - Extrae `objectid` como identificador único de la estación
   - Guarda el objeto JSON completo en el campo `data_raw` usando el tipo `Json()` de psycopg
   - Extrae el timestamp desde el campo `fecha_carg`
   - Ejecuta INSERT en la tabla `raw.valencia_air`

6. **Confirmación de transacción**: Si todas las inserciones son exitosas, ejecuta `connection.commit()`

7. **Rollback en caso de error**: Si cualquier inserción falla, ejecuta `connection.rollback()` para deshacer todos los cambios

**Aspectos técnicos importantes**:
- Usa `Json()` de psycopg para manejar correctamente el tipo JSONB de PostgreSQL
- El cursor se usa dentro de un context manager (`with`) que lo cierra automáticamente
- El bloque `finally` garantiza que la conexión se cierre incluso si hay errores
- Todas las inserciones ocurren en una sola transacción: o se guardan todas o ninguna

#### 3.2.6 Módulo ingestion/madrid.py

Implementa la lógica para extraer datos de la API de Madrid, que a diferencia de Valencia, retorna XML en lugar de JSON. Actualmente está implementada pero inactiva (`active: False` en config.py).

**Formato de la API**: La API de Madrid retorna XML con esta estructura:
```xml
<response>
  <medicion>
    <punto_muestreo>28079004_8_16</punto_muestreo>
    <fecha>2024-01-19</fecha>
    <hora>10</hora>
    <valor>25.5</valor>
    ...otros campos...
  </medicion>
</response>
```

**Diferencias clave con Valencia**:

1. **Parsing XML**: Utiliza `xml.etree.ElementTree` para parsear el contenido XML en lugar de `.json()`

2. **Extracción de elementos**: Busca todos los elementos `<medicion>` usando `root.findall('medicion')`

3. **Conversión a diccionario**: Para cada elemento `<medicion>`, extrae todos sus hijos y los convierte a un diccionario Python:
   ```python
   data_dict = {child.tag: child.text for child in med}
   ```

4. **Extracción del station_id**: El identificador de estación está codificado en el campo `punto_muestreo` con formato `estacion_magnitud_tecnica` (ejemplo: `28079004_8_16`). Se extrae dividiendo por `_` y tomando el primer elemento:
   ```python
   station_id = punto_muestreo.split('_')[0]  # Resultado: "28079004"
   ```

5. **Construcción del timestamp**: La fecha y hora vienen en campos separados, se concatenan para formar un timestamp válido:
   ```python
   timestamp_str = f"{fecha} {hora}:00"  # Resultado: "2024-01-19 10:00"
   ```

El resto del proceso es idéntico a Valencia: se inserta el diccionario en formato JSONB en `raw.madrid_air` y se confirma la transacción.

---

### 3.3 Transformaciones con dbt

**Ubicación**: Directorio `dbt/air_quality_dbt/`
**Configuración en docker-compose**: Líneas 22-35

dbt (data build tool) es una herramienta moderna de transformación de datos que permite escribir transformaciones SQL modulares y testeables. En este proyecto, dbt es responsable de tomar los datos crudos de la capa raw y transformarlos progresivamente hasta crear tablas analíticas listas para visualización.

**Configuración especial en Docker**:

El docker-compose sobrescribe el `entrypoint` de la imagen oficial de dbt con un script shell personalizado:
```bash
sleep 20;
while true; do
  dbt run && dbt docs generate --static;
  echo 'Transformación completada. Esperando 5 minutos...';
  sleep 300;
done
```

**¿Por qué sobrescribir el entrypoint?**
- La imagen oficial de dbt está diseñada para ejecutar un solo comando y terminar
- Nosotros necesitamos un proceso que se ejecute continuamente
- El script implementa un bucle infinito que ejecuta transformaciones cada 5 minutos

**Comportamiento del servicio**:
1. **Espera inicial de 20 segundos**: Da tiempo a que la aplicación Python inserte los primeros datos en raw
2. **Ejecución de transformaciones**: Ejecuta `dbt run` que materializa todos los modelos definidos
3. **Generación de documentación**: Ejecuta `dbt docs generate --static` que crea documentación HTML de todos los modelos
4. **Espera de 5 minutos**: `sleep 300` antes de repetir el ciclo
5. **Bucle infinito**: El `while true` hace que este proceso se repita indefinidamente

#### 3.3.1 Configuración de conexión (profiles.yml)

El archivo `profiles.yml` define cómo dbt se conecta a la base de datos PostgreSQL. Este archivo es fundamental porque dbt necesita saber dónde ejecutar las transformaciones SQL.

**Estructura del perfil**:
```yaml
air_quality_dbt:
  outputs:
    dev:
      type: postgres
      host: db           # Nombre del servicio Docker (no localhost)
      port: 5432         # Puerto interno del contenedor
      user: postgres
      pass: postgres
      dbname: air_quality_db
      schema: public
      threads: 1
  target: dev
```

**Aspectos importantes**:

- **host: db**: Usamos el nombre del servicio Docker, no `localhost`. Dentro de la red de Docker Compose, los servicios se comunican por nombre.
- **port: 5432**: Usamos el puerto interno del contenedor (5432), no el puerto expuesto del host (5431).
- **target: dev**: Indica qué configuración usar por defecto. En proyectos más grandes se tendrían múltiples targets (dev, staging, prod).
- **threads: 1**: Número de consultas SQL que dbt puede ejecutar en paralelo. Con 1 thread, los modelos se ejecutan secuencialmente.
- **schema: public**: Esquema por defecto, aunque los modelos pueden sobrescribir esto (como hacemos con staging, intermediate, marts).

#### 3.3.2 Configuración del proyecto (dbt_project.yml)

El archivo `dbt_project.yml` es el archivo de configuración principal del proyecto dbt. Define cómo se deben materializar y organizar los modelos.

**Configuración de materialización por capa**:

```yaml
models:
  air_quality_dbt:
    staging:
      +materialized: view
      +schema: staging
      +tags: ["staging"]

    intermediate:
      +materialized: table
      +schema: intermediate
      +tags: ["intermediate"]

    marts:
      +materialized: table
      +schema: marts
      +tags: ["marts"]
```

**Explicación de cada capa**:

**Staging**:
- **Materialización: view**: Los modelos staging se crean como vistas SQL, no tablas físicas
- **Ventaja de las vistas**: No duplican datos, solo proporcionan una forma estructurada de acceder a raw
- **Desventaja**: Las consultas son ligeramente más lentas porque se ejecutan cada vez
- **Esquema destino: staging**: dbt creará automáticamente un esquema llamado `staging` y pondrá allí estas vistas
- **Tags**: Permiten ejecutar solo modelos staging con `dbt run --select tag:staging`

**Intermediate**:
- **Materialización: table**: Se crean como tablas físicas en la base de datos
- **Ventaja**: Consultas rápidas porque los datos ya están materializados
- **Desventaja**: Ocupan más espacio en disco
- **Uso**: Esta capa unifica múltiples fuentes y hace transformaciones complejas, por eso se materializa como tabla

**Marts**:
- **Materialización: table**: Tablas físicas optimizadas para consultas de negocio
- **Razón**: Son las tablas que consulta Grafana, deben ser rápidas
- **Contienen**: Métricas agregadas (promedios, máximos, conteos) calculadas con GROUP BY
- **Esquema destino: marts**: Todas las tablas analíticas van al esquema `marts`

#### 3.3.3 Capa Staging

**Archivo**: models/staging/stg_valencia_air.sql

**Propósito**: Extraer y tipificar campos desde el JSONB crudo.

**Proceso**:
1. Lee desde raw.valencia_air usando la función source() de dbt
2. Utiliza jsonb_extract_path_text() para extraer cada campo del JSON
3. Realiza conversión de tipos explícita:
   - TEXT para identificadores y nombres
   - FLOAT para magnitudes de contaminantes
   - TIMESTAMP WITH TIME ZONE para fechas

**Campos extraídos**:
- station_id: Identificador de estación
- station_name: Nombre de la estación
- no2: Dióxido de nitrógeno
- pm10: Material particulado de 10 micras
- pm25: Material particulado de 2.5 micras
- so2: Dióxido de azufre
- o3: Ozono
- co: Monóxido de carbono
- air_quality_status: Estado de calidad del aire
- measure_timestamp: Momento de la medición
- ingested_at: Momento de ingesta en la base de datos

**Archivo**: models/staging/sources.yml

Define las fuentes de datos que dbt puede referenciar:

- Nombre de fuente: air_quality
- Base de datos: air_quality_db
- Esquema: raw
- Tablas:
  - valencia_air (con tests de not_null y unique en station_id)
  - madrid_air (comentada, inactiva)

#### 3.3.4 Capa Intermediate

**Archivo**: models/intermediate/int_air_quality_union.sql

**Propósito**: Unificar datos de múltiples ciudades en una estructura común.

**Estrategia**:

1. **CTE valencia_data**:
   - Selecciona todos los campos desde stg_valencia_air
   - Añade columna literal 'Valencia' como city

2. **CTE madrid_placeholder**:
   - Define la estructura con los mismos campos
   - Usa NULL con tipado explícito para cada columna
   - Incluye WHERE FALSE para que no retorne filas
   - Permite que la estructura esté preparada sin datos reales

3. **Unión final**:
   - Usa UNION ALL para combinar ambas CTEs
   - UNION ALL es más eficiente que UNION porque no elimina duplicados

**Resultado**: Tabla unificada con columna city que permite diferenciar el origen de cada registro.

#### 3.3.5 Capa Marts

**Archivo**: models/marts/fct_air_quality_daily.sql

**Propósito**: Agregar métricas por día para análisis de tendencias históricas.

**Transformaciones aplicadas**:

1. Agrupa por:
   - measure_date (fecha sin hora)
   - city
   - station_id
   - station_name

2. Calcula métricas agregadas:
   - Promedios diarios: AVG(no2), AVG(pm10), AVG(pm25)
   - Redondea a 2 decimales con ROUND()
   - Picos máximos: MAX(no2), MAX(pm10)

3. Filtra registros con timestamp nulo

4. Ordena por fecha descendente y ciudad

**Uso**: Esta tabla es ideal para dashboards que muestren evolución diaria de contaminantes.

**Archivo**: models/marts/fct_air_quality_hourly.sql

Similar a la tabla diaria pero con agregación por hora (no mostrado en el análisis pero mencionado en la estructura).

---

### 3.4 Visualización con Grafana

**Configuración en docker-compose**: Líneas 37-51

Grafana proporciona la interfaz de visualización para explorar los datos procesados.

**Configuración del servicio**:
- Imagen: grafana/grafana-oss:latest
- Puerto expuesto: 3000
- Usuario administrador: admin
- Contraseña: admin (puede cambiarse en primer acceso)

**Volúmenes montados**:
- ./grafana/provisioning/datasources: Configuración automática de conexión a PostgreSQL
- ./grafana/provisioning/dashboards: Definición de dashboards pre-configurados
- ./grafana/dashboards: Archivos JSON de dashboards
- grafana_data: Volumen persistente para datos de configuración

**Fuente de datos**:
Conecta directamente al servicio "db" dentro de la red Docker, consultando las tablas del esquema marts para obtener datos agregados listos para visualización.

---

## 4. FLUJO COMPLETO DE DATOS

El sistema procesa datos siguiendo este flujo secuencial:

**Fase 1: Extracción (cada ejecución de la app)**

1. El orquestador (main.py) verifica la infraestructura de base de datos
2. Lee la configuración de ciudades activas desde config.py
3. Para cada ciudad activa:
   - Llama a su API específica
   - Recibe JSON o XML
   - Inserta datos crudos en tablas raw.* con formato JSONB

**Fase 2: Transformación (cada 5 minutos, automático con dbt)**

1. Staging:
   - stg_valencia_air extrae campos específicos del JSONB
   - Tipifica cada campo correctamente
   - Materializa como vista SQL

2. Intermediate:
   - int_air_quality_union unifica todas las ciudades
   - Añade dimensión city
   - Materializa como tabla física

3. Marts:
   - fct_air_quality_daily agrega por día
   - fct_air_quality_hourly agrega por hora
   - Ambas materializadas como tablas físicas

**Fase 3: Visualización (continua)**

Grafana consulta las tablas marts.* en tiempo real y muestra:
- Evolución temporal de contaminantes
- Comparación entre estaciones
- Alertas de picos de contaminación
- Tendencias históricas

---

## 5. INSTRUCCIONES DE DESPLIEGUE

### 5.1 Requisitos previos

Antes de iniciar el proyecto, asegúrate de tener:

- **Docker Desktop** instalado y en ejecución (abrir la aplicación Docker Desktop)
- **Docker Compose** instalado (viene incluido con Docker Desktop en Windows y Mac)
- **Puertos libres**: 3000 (Grafana) y 5431 (PostgreSQL)
  
  - Verificar que no estén ocupados por otros proyectos o servicios
  - En Windows: `netstat -ano | findstr :3000`
  - En Linux/Mac: `lsof -i :3000`

### 5.2 Iniciar el sistema completo

Desde el directorio raíz del proyecto (donde está el archivo `docker-compose.yml`), ejecutar:

```bash
docker-compose up -d
```

**Significado del comando**:
- `docker-compose up`: Inicia todos los servicios definidos en docker-compose.yml

![alt text](image.png)

- `-d` (detached): Ejecuta los contenedores en segundo plano, liberando la terminal para seguir trabajando

![alt text](image-1.png)

**Servicios que se inician**:
1. **Base de datos PostgreSQL** (puerto 5431)
2. **Aplicación de ingestión Python** (ejecuta una vez y termina)
3. **Servicio dbt** (bucle continuo de transformaciones cada 5 minutos)
4. **Servidor Grafana** (puerto 3000)

**Primera ejecución**: La primera vez puede tardar varios minutos porque Docker debe descargar las imágenes base (postgres, dbt, grafana).

### 5.3 Verificar estado de servicios

Para verificar que todos los contenedores están corriendo correctamente:

```bash
docker-compose ps
```

**Salida esperada**:
```
NAME           STATUS          PORTS
db             Up 2 minutes    0.0.0.0:5431->5432/tcp
app            Exited (0)
dbt            Up 2 minutes
grafana        Up 2 minutes    0.0.0.0:3000->3000/tcp
```

**Interpretación**:
- `Up`: El contenedor está corriendo
- `Exited (0)`: El contenedor terminó correctamente (normal para app que ejecuta una vez)
- `Exited (1)`: El contenedor terminó con error (revisar logs)

### 5.4 Consultar logs

Los logs son fundamentales para diagnosticar problemas y verificar que todo funciona correctamente.

**Ver logs de todos los servicios**:
```bash
docker-compose logs -f
```

**Ver logs de un servicio específico**:
```bash
docker-compose logs -f app      # Ver si la ingesta funcionó
docker-compose logs -f dbt      # Ver transformaciones
docker-compose logs -f db       # Ver consultas SQL
docker-compose logs -f grafana  # Ver inicio de Grafana
```

**Significado del parámetro `-f` (follow)**:
- Muestra los logs en tiempo real a medida que se generan
- Ideal para ver si la ingesta de la API funciona o si hay errores
- Presionar `Ctrl+C` para salir del modo follow

![alt text](image-2.png)

**Ver solo las últimas líneas**:
```bash
docker-compose logs --tail=50 app  # Últimas 50 líneas
```

### 5.5 Reconstruir imágenes tras cambios en código

Si modificas archivos Python (`main.py`, `database.py`, etc.) o el `Dockerfile`, Docker necesita reconstruir la imagen para incluir los cambios:

```bash
docker-compose build      # Reconstruye las imágenes
docker-compose up -d      # Reinicia con las nuevas imágenes
```

![alt text](image-3.png)

**Flujo completo de actualización**:
```bash
# 1. Detener servicios
docker-compose down

# 2. Reconstruir imágenes
docker-compose build

# 3. Iniciar con nuevas imágenes
docker-compose up -d

# 4. Verificar logs
docker-compose logs -f app
```

### 5.6 Detener el sistema

**Detener sin eliminar datos**:
```bash
docker-compose down
```
Esto detiene y elimina los contenedores, pero mantiene los volúmenes (datos de PostgreSQL y Grafana se conservan).

**Reseteo completo** (eliminar también datos):
```bash
docker-compose down -v
```

**Significado del parámetro `-v` (volumes)**:
- Elimina los volúmenes de Docker donde se guardan datos persistentes
- Se usa cuando quieres empezar desde cero
- **Precaución**: Borra todos los datos de la base de datos y configuraciones de Grafana

![alt text](image-4.png)
---

## 6. EXTRACCIÓN Y CONSULTA DE INFORMACIÓN

### 6.1 Conexión directa a PostgreSQL

### 6.1.1 Desde la línea de comandos del host:

#### Ok varios cosas a explicar en caso de que no se tenga instalado PostgreSQL 

- Instalar psql localmente (si quieres usarlo desde fuera)

En cualquier sistema hay opcion Windows x86-64 y Mac OS X:
- Instalar PostgreSQL completo:

Pasos

- Descarga PostgreSQL desde https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
- Durante la instalación, marca solo "Command Line Tools"
- Reinicia la terminal

Ahora si puedes aplicar el comando que esta debajo

```bash
psql -h localhost -p 5431 -U postgres -d air_quality_db
```
Parámetros explicados:

-h localhost: Conecta al host local

-p 5431: Usa el puerto 5431 (el puerto expuesto en docker-compose)

-U postgres: Usuario postgres

-d air_quality_db: Base de datos air_quality_db

Cuando ejecutes el comando, te pedirá la contraseña: postgres

#### Contraseña: ----------->  postgres  <----------- AQUI 

### 6.1.2 Desde el contenedor de Docker:

```bash
docker-compose exec db psql -U postgres -d air_quality_db
``` 

Explicación:

- docker-compose exec db: Ejecuta un comando dentro del contenedor db

- psql -U postgres -d air_quality_db: Conecta a la base de datos

### 6.2 Consultas útiles

**Ver datos crudos recientes**:
```sql
SELECT
    station_id,
    data_raw->>'nombre' as estacion,
    timestamp
FROM raw.valencia_air
ORDER BY timestamp DESC
LIMIT 10;
```

**Ver datos limpios en staging**:
```sql
SELECT
    station_name,
    no2,
    pm10,
    pm25,
    measure_timestamp
FROM staging.stg_valencia_air
ORDER BY measure_timestamp DESC
LIMIT 10;
```

**Estadísticas diarias**:
```sql
SELECT
    measure_date,
    station_name,
    daily_avg_no2,
    daily_avg_pm10,
    max_pm10_peak
FROM marts.fct_air_quality_daily
WHERE measure_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY measure_date DESC, daily_avg_pm10 DESC;
```

**Conteo de registros por capa**:
```sql
SELECT 'raw' as capa, COUNT(*) as registros FROM raw.valencia_air
UNION ALL
SELECT 'staging', COUNT(*) FROM staging.stg_valencia_air
UNION ALL
SELECT 'marts_daily', COUNT(*) FROM marts.fct_air_quality_daily;
```

**Identificar estaciones con peor calidad**:
```sql
SELECT
    station_name,
    city,
    daily_avg_pm10,
    daily_avg_no2,
    measure_date
FROM marts.fct_air_quality_daily
WHERE measure_date = CURRENT_DATE
ORDER BY daily_avg_pm10 DESC
LIMIT 5;
```

### 6.3 Ejecución manual de transformaciones dbt

Acceder al contenedor dbt:
```bash
docker-compose exec dbt /bin/sh
```

Una vez dentro del contenedor:

```bash
# Ejecutar todos los modelos
dbt run

# Ejecutar solo modelos de una capa
dbt run --select staging
dbt run --select marts

# Ver modelos disponibles
dbt ls

# Ejecutar tests de calidad de datos
dbt test

# Generar documentación
dbt docs generate
```

### 6.4 Acceso a Grafana

1. Abrir navegador en http://localhost:3000
2. Introducir credenciales:
   - Usuario: admin
   - Contraseña: admin
3. En primer acceso, se solicitará cambiar la contraseña
4. Navegar a Connections > Data sources para verificar conexión a PostgreSQL
5. Crear dashboards consultando esquema marts

---

## 7. ESTRUCTURA DE DIRECTORIOS

```
Data-Project-1-Calidad-del-aire/
├── app/
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── valencia.py
│   │   └── madrid.py
│   ├── config.py
│   ├── database.py
│   ├── main.py
│   ├── utils.py
│   └── Dockerfile
├── dbt/
│   ├── air_quality_dbt/
│   │   ├── models/
│   │   │   ├── staging/
│   │   │   │   ├── sources.yml
│   │   │   │   └── stg_valencia_air.sql
│   │   │   ├── intermediate/
│   │   │   │   └── int_air_quality_union.sql
│   │   │   └── marts/
│   │   │       ├── fct_air_quality_daily.sql
│   │   │       ├── fct_air_quality_hourly.sql
│   │   │       └── marts.yml
│   │   ├── profiles.yml
│   │   └── dbt_project.yml
│   └── main.py
├── backend/
│   ├── database.py
│   ├── main.py
│   └── Dockerfile
├── frontend/
│   ├── app.py
│   └── Dockerfile
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/
│   │   └── dashboards/
│   └── dashboards/
├── .env
├── .gitignore
├── docker-compose.yml
└── README.md
```

---

## 8. ASPECTOS TÉCNICOS DESTACABLES

### 8.1 Gestión de dependencias entre servicios

El archivo docker-compose.yml establece dependencias explícitas:
- app depende de db
- dbt depende de app
- grafana depende de db

Esto asegura que los servicios se inicien en el orden correcto.

### 8.2 Manejo de errores y reintentos

Tanto las conexiones a base de datos como las llamadas a APIs implementan lógica de reintentos exponenciales. Esto hace el sistema resiliente ante:
- Retrasos en el inicio de PostgreSQL
- Caídas temporales de APIs externas
- Problemas de red transitorios

### 8.3 Almacenamiento flexible con JSONB

El uso de JSONB en la capa raw permite:
- Ingerir datos sin conocer su esquema completo de antemano
- Añadir nuevas ciudades sin modificar la estructura de tablas
- Consultar campos específicos con operadores JSON de PostgreSQL
- Mantener el payload original para auditoría

### 8.4 Separación de responsabilidades

Cada componente tiene un rol claramente definido:
- Python: Extracción e ingesta
- PostgreSQL: Almacenamiento persistente
- dbt: Transformación y modelado
- Grafana: Visualización

Esta separación facilita el mantenimiento y escalado independiente de cada capa.

### 8.5 Configuración centralizada

El archivo .env y config.py centralizan toda la configuración, facilitando:
- Migración a diferentes entornos (desarrollo, producción)
- Cambio de credenciales sin tocar código
- Activación/desactivación de ciudades sin modificar lógica

---

## 9. POSIBLES MEJORAS Y EXTENSIONES

### 9.1 Añadir nuevas ciudades

Para integrar una nueva ciudad:

1. Añadir entrada en CITIES_CONFIG (config.py)
2. Crear función de ingestión en ingestion/nombre_ciudad.py
3. Registrar función en INGESTION_MAP (main.py)
4. Añadir tabla en f_crear_tablas() (database.py)
5. Crear modelo staging en dbt
6. Actualizar int_air_quality_union.sql

### 9.2 Automatización de ingesta

Actualmente la app se ejecuta una vez. Posibles mejoras:
- Añadir bucle con sleep() en main.py
- Usar cron dentro del contenedor
- Implementar Airflow para orquestación compleja

### 9.3 Alertas y notificaciones

Implementar sistema de alertas cuando:
- Niveles de contaminación superen umbrales
- APIs fallen durante tiempo prolongado
- Transformaciones dbt detecten anomalías

### 9.4 API REST (backend comentado)

El docker-compose incluye un servicio backend comentado que podría:
- Exponer endpoints REST para consultar datos
- Servir de intermediario entre frontend y base de datos
- Implementar autenticación y autorización

### 9.5 Frontend interactivo

El servicio frontend comentado podría:
- Crear dashboards personalizados con Dash/Plotly
- Permitir selección dinámica de estaciones
- Mostrar mapas con geolocalización de estaciones

---

## 10. CONCLUSIONES

Este proyecto implementa una arquitectura moderna de pipeline de datos que:

- Integra múltiples fuentes de datos heterogéneas (JSON, XML)
- Aplica transformaciones progresivas siguiendo el patrón Medallion
- Garantiza calidad de datos mediante tests automatizados con dbt
- Proporciona visualización flexible con Grafana
- Es escalable y extensible a nuevas ciudades
- Utiliza contenedores Docker para portabilidad
- Implementa mejores prácticas de ingeniería de datos

La separación en capas (raw, staging, intermediate, marts) permite que diferentes perfiles técnicos trabajen en distintas fases del pipeline sin interferencias, y facilita el debugging al poder inspeccionar datos en cada etapa de transformación.

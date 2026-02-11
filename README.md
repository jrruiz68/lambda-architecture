# 🏥 Medical IoT: Arquitectura Lambda para Detección de Arritmias

Este proyecto implementa una Arquitectura Lambda completa para la ingestión, procesamiento y análisis de señales de electrocardiograma (ECG) en tiempo real. Utiliza datos clínicos reales (MIT-BIH), transmite eventos vía Kafka, detecta anomalías cardíacas mediante modelos de Machine Learning (Isolation Forest) y visualiza los resultados en vivo con Grafana.

## 🏗 Arquitectura del Sistema

El flujo de datos sigue el patrón estándar de IoT industrial:

- **Fuente de Datos (Sensor):** Script en Python que simula un monitor Holter leyendo archivos médicos (`.dat`) y enviando telemetría.
- **Capa de Ingesta:** Apache Kafka gestiona el flujo de alta velocidad de los datos biométricos.
- **Capa de Procesamiento (Speed Layer):** Consumidor inteligente que utiliza modelos de Scikit-Learn gestionados por MLflow para inferencia en tiempo real.
- **Capa de Almacenamiento (Serving):** PostgreSQL persiste los datos crudos y las alertas de anomalías.
- **Visualización:** Grafana consulta la base de datos para mostrar el ECG y las alertas rojas en tiempo real.
- **Orquestación:** Docker Compose para infraestructura y un Launcher GUI (Tkinter) para el control de procesos.

## 📋 Requisitos Previos

Antes de comenzar, asegúrate de tener instalado:

- **Docker Desktop** (Debe estar ejecutándose).
- **Python 3.8** o superior.
- **Git** (Opcional).

## ⚙️ Instalación y Configuración

### 1. Clonar/Preparar el Proyecto

Asegúrate de tener la siguiente estructura de carpetas:

```plaintext
proyecto_iot_medico/
├── data/
│   ├── raw/           # Aquí irán los archivos del dataset
│   └── postgres/      # (Se crea automática) Datos de la BD
├── streaming/
│   ├── ecg_producer.py
│   └── anomaly_detector.py
├── batch/
│   ├── train_model.py
│   └── mlflow.db      # (ARCHIVO VACÍO, ver paso 3)
├── main_launcher.py   # Centro de Control GUI
└── docker-compose.yml
```

### 2. Instalar Dependencias de Python

Ejecuta en tu terminal:

```bash
pip install wfdb kafka-python numpy scikit-learn mlflow psycopg2-binary
```

> **Nota:** `tkinter` suele venir incluido con Python. Si falla, instálalo según tu sistema operativo.

### 3. Configurar Base de Datos MLflow

MLflow requiere un archivo para su base de datos local.

1. Ve a la carpeta `batch/`.
2. Crea un archivo vacío llamado `mlflow.db`.

> ⚠️ **Importante:** Asegúrate de que **NO** sea una carpeta. Si existe una carpeta con ese nombre, bórrala.

### 4. Descargar Datos Médicos (PhysioNet)

Necesitamos datos reales de pacientes.

1. Ve al [MIT-BIH Arrhythmia Database](https://www.physionet.org/content/mitdb/).
2. Descarga los archivos `100.dat` y `100.hea`.
3. Colócalos en la carpeta: `proyecto_iot_medico/data/raw/`.

## 🚀 Ejecución del Proyecto

### Paso 1: Levantar la Infraestructura

Inicia los servicios de backend (Kafka, Postgres, Grafana, MLflow):

```bash
docker-compose up -d
```

> Espera unos 30 segundos para que Kafka termine de iniciarse correctamente.

### Paso 2: El Centro de Control (Launcher)

Para facilitar la operación, usa el lanzador gráfico:

```bash
python main_launcher.py
```

### Paso 3: Flujo de Operación (En la GUI)

1. **Clic en "🧠 1. Entrenar Modelo":**
   - Esto leerá los datos históricos y creará un "cerebro" (modelo Isolation Forest).
   - Verifica en el log de la izquierda que diga: `✅ Modelo entrenado y enviado a MLflow`.

2. **Clic en "💓 2. Iniciar Sensor":**
   - Comenzará a leer el ECG y enviarlo a Kafka. Verás el log verde en el centro.

3. **Clic en "🔎 3. Iniciar Detector":**
   - Comenzará a analizar los datos en vivo. Verás el log naranja a la derecha.
   - Puntos `.` indican latidos normales.
   - Mensajes `🚨 ANOMALÍA DETECTADA` indican arritmias.

## 📊 Configuración de Grafana (Visualización)

Una vez que el sistema está corriendo, configura el dashboard visual.

1. **Acceso:** Abre http://localhost:3000 (User: `admin` / Pass: `admin`).
2. **Conexión a Datos:**
   - Ve a **Connections > Data Sources > Add new**.
   - Selecciona **PostgreSQL**.
   - **Host:** `postgres:5432`
   - **Database:** `medical_iot`
   - **User/Password:** `admin` / `admin`
   - **TLS/SSL Mode:** `disable`
   - Click **Save & Test**.

3. **Crear el Dashboard ECG:**
   - Crea un **New Dashboard > Add Visualization**.
   - Selecciona la base de datos PostgreSQL.
   - Pega la siguiente consulta SQL:

   ```sql
   SELECT timestamp AS "time", ecg_value AS "Ritmo Cardíaco" FROM cardiac_anomalies ORDER BY timestamp ASC
   ```

4. **Agregar Capa de Anomalías (Puntos Rojos):**
   - Click en `+ Query` para añadir una segunda consulta:

   ```sql
   SELECT timestamp AS "time", ecg_value AS "ANOMALÍA" FROM cardiac_anomalies WHERE is_anomaly = true ORDER BY timestamp ASC
   ```

   - A la derecha, ve a **Overrides > + Add override field > ANOMALÍA**.
   - Agrega propiedad: **Graph styles > Style > Points**.
   - Agrega propiedad: **Graph styles > Point size > 10**.
   - Agrega propiedad: **Standard options > Color scheme > Single Color > Red**.

5. **Activar Tiempo Real:**
   - En el dashboard, cambia el rango de tiempo a **Last 5 minutes**.
   - Haz clic en el icono de refresco 🔄 y selecciona **5s**.

## 🔧 Solución de Problemas

| Error | Causa Probable | Solución |
| :--- | :--- | :--- |
| **NoBrokersAvailable** | Kafka aún no ha arrancado. | Espera 30s o reinicia con `docker-compose restart kafka`. |
| **UnicodeEncodeError** | Consola de Windows antigua. | El `main_launcher.py` ya incluye el parche UTF-8. Úsalo para ejecutar. |
| **MLflow 404 Error** | Versiones diferentes cliente/server. | Asegúrate de usar `image: ghcr.io/mlflow/mlflow:latest` en docker-compose. |
| **Gráfica detenida** | El archivo de datos terminó. | El script ahora tiene un modo "Bucle Infinito", solo espera a que reinicie la lectura. |

## 📝 Justificación Técnica (Python vs Flink)

Aunque arquitecturas Lambda tradicionales usan Apache Flink en la capa de velocidad, este proyecto utiliza un Consumidor Python personalizado. Esto se debe a la necesidad de integrar librerías de Inteligencia Artificial (Scikit-Learn/MLflow) para la detección de anomalías complejas, una tarea donde Python ofrece mayor flexibilidad y soporte de librerías que Java/Scala en Flink.

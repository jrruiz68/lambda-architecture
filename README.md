# Medical IoT: Arquitectura Lambda Pura para Detección de Arritmias

Este proyecto implementa una **Arquitectura Lambda** de libro de texto para la ingestión, procesamiento y análisis de señales de electrocardiograma (ECG) en tiempo real. Utiliza datos clínicos reales (MIT-BIH), transmite eventos vía **Kafka** y realiza una bifurcación estricta: por un lado, detecta anomalías en milisegundos mediante modelos de **Machine Learning** (Speed Layer); por otro, almacena un **Data Lake** inmutable para el cálculo preciso de resúmenes diarios (Batch Layer).

## 🏗 Arquitectura del Sistema

El flujo de datos sigue el patrón estándar de la Arquitectura Lambda:

*   **Fuente de Datos (Sensor):** Script en Python que simula un monitor Holter leyendo archivos médicos (`.dat`) y enviando telemetría en bucle infinito.
*   **Capa de Ingesta:** Apache Kafka gestiona el flujo de alta velocidad de los datos biométricos.
*   **Bifurcación 1 - Capa de Procesamiento (Speed Layer):** Consumidor inteligente que utiliza un modelo *Isolation Forest* (Scikit-Learn) gestionado por **MLflow** para inferencia en tiempo real.
*   **Bifurcación 2 - Capa Batch (Data Lake & Proceso Diario):** Un consumidor paralelo (`raw_to_datalake.py`) guarda los datos crudos en formato JSONL. Un procesador diario (`batch_daily_processor.py`) utiliza Pandas para calcular la "verdad absoluta" (estadísticas pesadas) sobre estos datos masivos.
*   **Capa de Almacenamiento (Serving):** PostgreSQL persiste tanto las alertas en tiempo real como los resúmenes agregados diarios.
*   **Visualización:** Grafana consulta la base de datos para mostrar el ECG en vivo y los puntos de alerta.
*   **Orquestación:** Docker Compose para infraestructura y un **Lambda Command Center** (GUI Dark Mode) para el control unificado de los procesos.

## 📋 Requisitos Previos

Antes de comenzar, asegúrate de tener instalado:

*   **Docker Desktop** (Debe estar ejecutándose).
*   **Python 3.8** o superior.
*   **Git** (Opcional).

## ⚙️ Instalación y Configuración

### 1. Clonar/Preparar el Proyecto

Asegúrate de tener la siguiente estructura de carpetas actualizada:

```text
proyecto_iot_medico/
├── data/
│   ├── raw/           # Aquí irán los archivos MIT-BIH (.dat y .hea)
│   ├── datalake/      # (Se crea automáticamente) Archivos crudos JSONL por día
│   └── postgres/      # (Se crea automáticamente) Datos de la BD
├── streaming/
│   ├── ecg_producer.py
│   ├── anomaly_detector.py
│   └── raw_to_datalake.py  # Ingestor del Data Lake
├── batch/
│   ├── train_model.py
│   ├── batch_daily_processor.py # Recálculo diario
│   └── mlflow.db      # (ARCHIVO VACÍO)
├── main_launcher.py   # Command Center GUI
└── docker-compose.yml
```

### 2. Instalar Dependencias de Python

Ejecuta en tu terminal:

```bash
pip install wfdb kafka-python numpy scikit-learn mlflow psycopg2-binary pandas
```

> [!NOTE]
> `tkinter` suele venir incluido con Python. Si falla, instálalo según tu sistema operativo.

### 3. Configurar Base de Datos MLflow

MLflow requiere un archivo para su base de datos local.

1.  Ve a la carpeta `batch/`.
2.  Crea un archivo vacío llamado `mlflow.db`.
3.  ⚠️ **Importante:** Asegúrate de que NO sea una carpeta. Si existe una carpeta con ese nombre, bórrala y crea el archivo.

### 4. Descargar Datos Médicos (PhysioNet)

Necesitamos datos reales de pacientes.

1.  Ve al [MIT-BIH Arrhythmia Database](https://archive.physionet.org/cgi-bin/atm/ATM).
2.  Descarga los archivos `100.dat` y `100.hea`.
3.  Colócalos en la carpeta: `proyecto_iot_medico/data/raw/`.

---

## 🚀 Ejecución del Proyecto

### Paso 1: Levantar la Infraestructura

Inicia los servicios de backend (Kafka, Postgres, Grafana, MLflow):

```bash
docker-compose up -d
```

*Espera unos 30 segundos para que Kafka termine de iniciarse correctamente.*

### Paso 2: El Centro de Comando (Launcher)

Para orquestar toda la arquitectura, usa el lanzador gráfico:

```bash
python main_launcher.py
```

### Paso 3: Flujo de Operación (En la GUI)

El dashboard interactivo refleja las fases exactas de la arquitectura Lambda:

1.  **Clic en "▶ START" en [1. Pre-Entrenamiento]:** Aprende de los datos históricos y envía el cerebro a MLflow.
2.  **Clic en "▶ START" en [2. Sensor ECG (Fuente)]:** Comienza a enviar latidos a Kafka.
3.  **Activar la Bifurcación (Ejecutar ambos al mismo tiempo):**
    *   Clic en "▶ START" en **[3A. Data Lake Ingest]**: Guarda la copia inmutable.
    *   Clic en "▶ START" en **[3B. Speed Layer (IA)]**: Analiza en milisegundos buscando arritmias.
4.  **Clic en "▶ START" en [4. Batch Processor (Diario)]:** Simula el proceso de fin de día. Lee el Data Lake completo, calcula promedios y máximos con Pandas, y consolida la tabla de resúmenes en la base de datos.

---

## 📊 Configuración de Grafana (Visualización)

1.  **Acceso:** Haz clic en el botón "📊 Abrir Grafana" del launcher o ve a [http://localhost:3000](http://localhost:3000) (User: `admin` / Pass: `admin`).
2.  **Conexión a Datos:**
    *   Ve a **Connections > Data Sources > Add new**.
    *   Selecciona **PostgreSQL**.
    *   **Host:** `postgres:5432`
    *   **Database:** `medical_iot`
    *   **User/Password:** `admin` / `admin`
    *   **TLS/SSL Mode:** `disable`
    *   Click **Save & Test**.
3.  **Crear el Dashboard ECG:**
    *   Crea un **New Dashboard > Add Visualization**.
    *   Selecciona **PostgreSQL** y usa la consulta:
        ```sql
        SELECT timestamp AS "time", ecg_value AS "Ritmo Cardíaco" 
        FROM cardiac_anomalies 
        ORDER BY timestamp ASC
        ```
4.  **Agregar Capa de Anomalías (Puntos Rojos):**
    *   Click en **+ Query** para añadir:
        ```sql
        SELECT timestamp AS "time", ecg_value AS "ANOMALÍA" 
        FROM cardiac_anomalies 
        WHERE is_anomaly = true 
        ORDER BY timestamp ASC
        ```
    *   A la derecha: **Overrides > + Add override field > Fields With Name > ANOMALÍA**.
    *   Propiedades a añadir: **Graph styles > Style > Points** | **Point size > 10** | **Color scheme > Single Color > Red**.
5.  **Activar Tiempo Real:**
    *   Cambia el rango de tiempo a **Last 5 minutes**.
    *   Haz clic en el icono de refresco 🔄 y selecciona **5s**.

## 📊 Visualización de la Capa Batch (Reporte Clínico Diario)

A diferencia de la *Speed Layer* (que muestra datos en vivo), la **Batch Layer** genera una "Verdad Absoluta" basada en el procesamiento completo del Data Lake. Esta vista es ideal para que los médicos analicen tendencias diarias sin el ruido de las transmisiones en tiempo real.

### Pasos para configurar el Reporte Diario en Grafana:

1. **Crear un nuevo Panel:**
   - En tu Dashboard de Grafana, haz clic en **Add > Visualization**.
   - Selecciona el origen de datos **PostgreSQL**.

2. **Configurar la Consulta SQL:**
   - Cambia al modo **Code** y pega la siguiente consulta, que extrae los cálculos procesados por el `batch_daily_processor.py`:

   ```sql
   SELECT 
     fecha AS "time",
     patient_id AS "Paciente",
     total_muestras AS "Muestras Procesadas",
     promedio_ecg AS "Media ECG",
     max_ecg AS "Pico Máximo",
     min_ecg AS "Pico Mínimo"
   FROM vitals_daily_batch
   ORDER BY fecha DESC


---

## 🔧 Solución de Problemas

| Error | Causa Probable | Solución |
| :--- | :--- | :--- |
| `NoBrokersAvailable` | Kafka aún no ha arrancado. | Espera 30s o reinicia con `docker-compose restart kafka`. |
| `UnicodeEncodeError` | Consola de Windows antigua. | El `main_launcher.py` ya incluye el parche UTF-8. Ejecuta siempre el proyecto desde ahí. |
| `MLflow 404 Error` | Versiones diferentes cliente/server. | Asegúrate de usar `image: ghcr.io/mlflow/mlflow:latest` en `docker-compose.yml`. |
| `Data Lake Vacío` | La ruta no existe o no hay datos. | El script crea la carpeta automáticamente, pero asegúrate de ejecutar el módulo 3A mientras el sensor está enviando datos. |

## 📝 Justificación Arquitectónica

Este proyecto cumple de forma estricta con el teorema de la Arquitectura Lambda:

*   **Inmutabilidad:** Los datos crudos se almacenan en un Data Lake (`.jsonl`) de forma permanente, permitiendo reprocesamientos futuros.
*   **Batch vs Speed:** Mientras Apache Flink es común en despliegues Java/Scala, aquí se justifica el uso de Python puro para la Speed Layer dado el requisito innegociable de ejecutar inferencias de Machine Learning de Scikit-Learn. El *Heavy Lifting* (procesamiento masivo) se delega a la **Batch Layer** utilizando Pandas para procesar el Data Lake independientemente.

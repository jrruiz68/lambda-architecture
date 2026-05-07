# 🏥 Medical IoT: Arquitectura Lambda Pura
### *Detección de Arritmias en Tiempo Real con Machine Learning*

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.12%2B-green.svg)
![Kafka](https://img.shields.io/badge/Streaming-Kafka-orange.svg)
![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-blue.svg)

Este proyecto implementa una **Arquitectura Lambda** completa para la ingestión, procesamiento y análisis de señales de electrocardiograma (ECG) en tiempo real. Utilizando datos clínicos del dataset **MIT-BIH**, el sistema bifurca el flujo de datos para ofrecer tanto respuestas inmediatas (Speed Layer) como análisis precisos de largo plazo (Batch Layer).

---

## 🏗️ Arquitectura del Sistema

El flujo de datos sigue el patrón estándar de la Arquitectura Lambda para garantizar escalabilidad y tolerancia a fallos:

- **📡 Fuente de Datos (Sensor):** Script en `data_sources/sensor_simulador.py` que simula un monitor Holter procesando archivos médicos `.dat` y enviando telemetría continua vía Kafka.
- **📥 Capa de Ingesta:** Apache Kafka gestiona el flujo de alta velocidad de los datos biométricos.
- **⚡ Speed Layer (Tiempo Real):** Inferencia en milisegundos mediante un modelo *Isolation Forest* (gestionado vía MLflow en el puerto 5001) para detección de anomalías usando una **Ventana Deslizante**.
- **📊 Batch Layer (Data Lake & Histórico):** Almacenamiento inmutable (retención `earliest`) para el cálculo diario de la "verdad absoluta" mediante procesamiento pesado.
- **🌐 Serving Layer:** PostgreSQL y FastAPI (`serving/query_api.py`) unifican ambas capas para exponer una vista clínica consolidada (Merge).

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
| :--- | :--- |
| **Streaming** | Apache Kafka |
| **Model Serving** | MLflow |
| **Procesamiento** | Python (Pandas, Scikit-Learn) |
| **Almacenamiento** | PostgreSQL (Data Lake en JSONL) |
| **Visualización** | Grafana |
| **API** | FastAPI |
| **Contenerización** | Docker & Docker Compose |

---

## 📁 Estructura del Proyecto

```text
lambda-architecture/
├── 📂 batch/            # Entrenamiento de IA (train_model.py), orquestador y proceso diario
├── 📂 data/             # Datos crudos (MIT-BIH), Data Lake inmutable y persistencia BD
├── 📂 data_sources/     # Script simulador de sensor escalable (sensor_simulador.py)
├── 📂 serving/          # API REST para consulta de vistas unificadas (query_api.py)
├── 📂 streaming/        # Speed Layer (anomaly_detector.py) y persistencia (raw_to_datalake.py)
├── 📄 main_launcher.py  # GUI de Control (Command Center)
├── 📄 docker-compose.yml # Orquestación de infraestructura (Kafka, DB, MLflow en p5001)
├── 📄 requirements.txt  # Dependencias del proyecto (usa kafka-python-ng)
└── 📄 .env.example      # Plantilla de variables de entorno
```

---

## ⚙️ Instalación y Configuración

> **Importante:** Asegúrate de tener Docker Desktop y Python 3.12+ instalados y en ejecución.

### 1. Variables de Entorno

Copia la plantilla de variables de entorno y ajusta las credenciales si es necesario:

```bash
cp .env.example .env
```

### 2. Clonar e Instalar Dependencias

> **Nota:** Se utiliza `kafka-python-ng` para garantizar la compatibilidad nativa con Python 3.12+.

```bash
pip install -r requirements.txt
```

### 3. Configurar Base de Datos MLflow y Datos Médicos

- Crea un archivo vacío llamado `mlflow.db` en la carpeta `batch/`.
- Descarga `100.dat` y `100.hea` de [MIT-BIH Arrhythmia Database](https://physionet.org/content/mitdb/1.0.0/).
- Colócalos en `data/raw/`.

---

## 🚀 Guía de Ejecución

Abre terminales separadas para ejecutar los componentes y observar el flujo de la arquitectura en acción:

### Paso 1: Levantar Infraestructura

```bash
docker-compose up -d
```

Espera ~30s a que Kafka inicie. MLflow estará disponible en `http://localhost:5001`.

### Paso 2: Entrenar el Modelo *(Requisito para Speed Layer)*

```bash
python batch/train_model.py
```

### Paso 3: Levantar la Serving Layer

```bash
python serving/query_api.py
```

### Paso 4: Iniciar el Flujo de Datos

```bash
# Fuente de Datos
python data_sources/sensor_simulador.py

# Data Lake
python streaming/raw_to_datalake.py

# Speed Layer
python streaming/anomaly_detector.py

# Orquestador Batch
python batch/scheduler.py
```

> **Nota:** Si usas la GUI `main_launcher.py`, puedes omitir el Paso 4 y controlar los procesos directamente desde la interfaz.

---

## 📊 Visualización y Consultas

### API (Serving Layer)

- **Swagger UI:** `http://localhost:8000/docs`
- **Endpoint Unificado (Merge Lambda):** `GET /unified/{patient_id}` *(Prueba con `PACIENTE-100`)*

### Grafana

**URL:** `http://localhost:3000` (usuario: `admin` / contraseña: `admin`)

**Query de Anomalías en Vivo (Speed Layer):**
```sql
SELECT timestamp AS "time", ecg_value AS "ANOMALÍA"
FROM cardiac_anomalies
WHERE is_anomaly = true
ORDER BY timestamp ASC
```

**Query de Tendencias (Batch Layer):**
```sql
SELECT fecha AS "time", promedio_ecg AS "Media ECG", max_ecg AS "Pico Máximo"
FROM vitals_daily_batch
ORDER BY fecha DESC
```

---

## 🔧 Solución de Problemas Frecuentes

| Error | Solución |
| :--- | :--- |
| `No module named 'kafka.vendor.six.moves'` | Desinstala `kafka-python` e instala `kafka-python-ng` (compatibilidad Python 3.12+). |
| `RESOURCE_DOES_NOT_EXIST: Run with id=latest` | Ejecuta `python batch/train_model.py` primero para registrar el modelo en la versión 1. |
| `MLflow connection error` | Asegúrate de que el puerto `5001` esté mapeado en `docker-compose.yml` y en tu archivo `.env`. |
| `NoBrokersAvailable` | Kafka tarda ~30s en iniciar dentro de Docker. Espera un momento y reintenta el script del sensor. |

---

## 📝 Justificación Arquitectónica

Este proyecto se adhiere a los pilares fundamentales de la Arquitectura Lambda:

- **Inmutabilidad:** Los datos en el Data Lake nunca se modifican, solo se añaden de forma segura (tolerancia a fallos con offset `earliest`).
- **Precisión:** La Batch Layer corrige cualquier posible deriva mediante un procesamiento pesado consolidado.
- **Inmediatez:** La Speed Layer (Ventana Deslizante) proporciona alertas críticas en milisegundos, latido a latido.

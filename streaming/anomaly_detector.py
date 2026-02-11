import json
import numpy as np
import time
import mlflow.sklearn
from kafka import KafkaConsumer
import psycopg2

# --- CONFIGURACIÓN ---
KAFKA_BROKER = 'localhost:9092'
TOPIC_INPUT = 'ecg_raw'  # El tema donde el simulador escribe
POSTGRES_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "database": "medical_iot",
    "user": "admin",
    "password": "admin"
}

# Configuración del Modelo (Debe coincidir con train_model.py)
MLFLOW_URI = "http://localhost:5000"
EXPERIMENT_NAME = "Deteccion_Arritmias_ECG"
WINDOW_SIZE = 100 

def get_latest_model():
    """Busca automáticamente el último modelo entrenado exitoso en MLflow"""
    print("🧠 Buscando el mejor cerebro disponible en MLflow...")
    mlflow.set_tracking_uri(MLFLOW_URI)
    client = mlflow.tracking.MlflowClient()
    
    # Busca el experimento por nombre
    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        raise Exception(f"No se encontró el experimento '{EXPERIMENT_NAME}'. ¿Ejecutaste train_model.py?")

    # Busca la última ejecución (Run)
    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=["attribute.start_time DESC"],
        max_results=1
    )
    
    if not runs:
        raise Exception("No hay modelos entrenados. Ejecuta 'python batch/train_model.py' primero.")
        
    latest_run_id = runs[0].info.run_id
    model_uri = f"runs:/{latest_run_id}/model_ecg"
    print(f"✅ Modelo cargado desde: {model_uri}")
    return mlflow.sklearn.load_model(model_uri)

def init_db():
    """Crea la tabla de resultados en Postgres si no existe"""
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cur = conn.cursor()
        # Creamos una tabla para guardar cada predicción
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cardiac_anomalies (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP,
                patient_id VARCHAR(50),
                ecg_value FLOAT,
                is_anomaly BOOLEAN,
                anomaly_score FLOAT
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("💾 Base de datos PostgreSQL lista.")
    except Exception as e:
        print(f"❌ Error conectando a Postgres: {e}")

def run_detector():
    # 1. Preparativos
    init_db()
    try:
        model = get_latest_model()
    except Exception as e:
        print(e)
        return

    # 2. Conectar a Kafka (Consumidor)
    print(f"📡 Conectando a Kafka ({KAFKA_BROKER})...")
    consumer = KafkaConsumer(
        TOPIC_INPUT,
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='latest' # Leer solo datos nuevos
    )
    
    print("🩺 Sistema de Detección de Arritmias ACTIVO. Esperando latidos...")
    
    # Búfer para acumular datos (El modelo necesita ver una ventana de tiempo, no un punto solo)
    buffer_values = []
    buffer_meta = [] # Para guardar timestamps y IDs
    
    # Conexión permanente a DB para insertar rápido
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    cur = conn.cursor()

    for message in consumer:
        data = message.value
        val = data['ecg_value']
        
        # Agregamos el dato al búfer
        buffer_values.append(val)
        buffer_meta.append(data)

        # Si ya tenemos suficientes datos (ej. 100 puntos = ~0.3 segundos de latido)
        if len(buffer_values) >= WINDOW_SIZE:
            # Preparamos los datos para el modelo
            X_pred = np.array(buffer_values).reshape(1, -1)
            
            # --- INFERENCIA (El Cerebro decide) ---
            # El modelo devuelve: 1 (Normal) o -1 (Anomalía)
            pred = model.predict(X_pred)[0]
            is_anomaly = True if pred == -1 else False
            
            # --- PERSISTENCIA (Guardar en Postgres) ---
            # Guardamos el dato central de la ventana
            mid_index = WINDOW_SIZE // 2
            record = buffer_meta[mid_index]
            
            query = """
                INSERT INTO cardiac_anomalies (timestamp, patient_id, ecg_value, is_anomaly, anomaly_score)
                VALUES (to_timestamp(%s), %s, %s, %s, %s)
            """
            cur.execute(query, (
                record['timestamp'], 
                record['patient_id'], 
                record['ecg_value'], 
                is_anomaly, 
                float(pred)
            ))
            conn.commit()

            # Feedback visual en la consola
            if is_anomaly:
                print(f"🚨 ANOMALÍA DETECTADA | Paciente: {record['patient_id']} | Valor: {record['ecg_value']:.2f}")
            else:
                # Imprimir un punto para saber que sigue vivo sin llenar la pantalla
                print(".", end="", flush=True)

            # Limpiamos el búfer para la siguiente ventana
            # (En producción usaríamos ventanas deslizantes, aquí simplificamos borrando)
            buffer_values = []
            buffer_meta = []

if __name__ == "__main__":
    run_detector()
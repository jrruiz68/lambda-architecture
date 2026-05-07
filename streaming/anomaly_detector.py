"""
=========================================================
SPEED LAYER: DETECTOR DE ANOMALÍAS EN TIEMPO REAL
=========================================================
Este módulo implementa la Speed Layer de la Arquitectura Lambda.

- Consume datos en tiempo real desde Kafka.
- Utiliza un modelo de Machine Learning (Isolation Forest) desde MLflow.
- Implementa una VENTANA DESLIZANTE para análisis continuo.
- Provee inmediatez en la detección de eventos críticos.
"""

import json
import os
import time
import pandas as pd
import numpy as np
import mlflow
import mlflow.sklearn
import psycopg2
from kafka import KafkaConsumer
from collections import deque
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# --- CONFIGURACIÓN ---
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC_INPUT = os.getenv("KAFKA_TOPIC_RAW", "ecg_raw")
MLFLOW_URI = os.getenv("MLFLOW_URI", "http://localhost:5001")
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "medical_iot"),
    "user": os.getenv("DB_USER", "admin"),
    "password": os.getenv("DB_PASSWORD", "admin")
}

# Parámetros del modelo
WINDOW_SIZE = 100  # Debe coincidir con el entrenamiento en batch/train_model.py

# --- GESTIÓN DE MODELO ---
def load_latest_model():
    print(f"[SPEED LAYER] Conectando a MLflow en {MLFLOW_URI}...")
    mlflow.set_tracking_uri(MLFLOW_URI)
    try:
        # Definimos la URI apuntando al registro de modelos (Punto 2 y 3 de mejoras)
        model_name = "model_ecg"
        model_uri = f"models:/{model_name}/1" 
        
        # CAMBIO AQUÍ: Usamos la variable model_uri que definimos arriba
        model = mlflow.sklearn.load_model(model_uri) 
        
        print(f"✅ Modelo '{model_name}' (v1) cargado exitosamente desde el Registro de MLflow.")
        return model
    except Exception as e:
        print(f"⚠️ No se pudo cargar el modelo desde MLflow: {e}")
        print("Falla crítica: Asegúrate de haber ejecutado el entrenamiento primero.")
        return None

# --- GESTIÓN DE BASE DE DATOS ---
def save_anomaly(patient_id, timestamp, ecg_value, is_anomaly):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Crear tabla si no existe (Serving Layer - Real-time View)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cardiac_anomalies (
                id SERIAL PRIMARY KEY,
                patient_id VARCHAR(50),
                timestamp TIMESTAMP,
                ecg_value FLOAT,
                is_anomaly BOOLEAN
            );
        """)
        
        cur.execute("""
            INSERT INTO cardiac_anomalies (patient_id, timestamp, ecg_value, is_anomaly)
            VALUES (%s, %s, %s, %s)
        """, (patient_id, timestamp, ecg_value, is_anomaly))
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error guardando en DB: {e}")

# --- PROCESAMIENTO STREAMING ---
def run_anomaly_detector():
    model = load_latest_model()
    if not model:
        return

    print(f"[SPEED LAYER] Escuchando stream en {TOPIC_INPUT}...")
    
    consumer = KafkaConsumer(
        TOPIC_INPUT,
        bootstrap_servers=[KAFKA_BROKER],
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='latest' # En la Speed Layer nos interesa lo más reciente
    )

    # Diccionario para mantener ventanas deslizantes por paciente
    # Permite escalar a múltiples sensores simultáneos
    patient_buffers = {}

    for message in consumer:
        data = message.value
        p_id = data['patient_id']
        val = data['ecg_value']
        ts = data['timestamp']

        if p_id not in patient_buffers:
            patient_buffers[p_id] = deque(maxlen=WINDOW_SIZE)
        
        # Agregar a la ventana deslizante
        patient_buffers[p_id].append(val)

        # Cuando la ventana está llena, realizamos la inferencia
        if len(patient_buffers[p_id]) == WINDOW_SIZE:
            # Convertir buffer a formato esperado por el modelo (1, WINDOW_SIZE)
            input_data = np.array(list(patient_buffers[p_id])).reshape(1, -1)
            
            # Predict: Isolation Forest devuelve -1 para anomalía, 1 para normal
            prediction = model.predict(input_data)
            is_anomaly = bool(prediction[0] == -1)

            if is_anomaly:
                print(f"🚨 ANOMALÍA DETECTADA | Paciente: {p_id} | Valor: {val:.4f}")
            
            # Guardamos el resultado en la Serving Layer
            save_anomaly(p_id, ts, val, is_anomaly)

if __name__ == "__main__":
    run_anomaly_detector()
"""
=========================================================
FUENTE DE DATOS: SENSOR SIMULADOR (DATA SOURCE)
=========================================================
Este módulo representa el origen de los datos en la arquitectura Lambda.

- Actúa como un generador de flujo continuo de datos (Data Stream), 
  simulando el comportamiento de sensores de monitoreo cardíaco reales.
- El diseño es capaz de escalar a múltiples instancias (N sensores). 
  Al ejecutar varios scripts en paralelo con distintos 'patient_id', 
  se simula un entorno hospitalario de alta concurrencia.
"""

import time
import json
import wfdb
from datetime import datetime
from kafka import KafkaProducer
import os
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURACIÓN (Se moverá a .env en el Punto 6) ---
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC_NAME = os.getenv("KAFKA_TOPIC_RAW", "ecg_raw")
RECORD_PATH = 'data/raw/100'

def run_sensor(patient_id="PACIENTE-100"):
    print(f"[DATA SOURCE] Iniciando simulador de sensor para {patient_id}...")
    
    # 1. Conexión al Bus de Mensajes (Kafka)
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print(f"Conectado al broker en {KAFKA_BROKER}.")
    except Exception as e:
        print(f"Error conectando a Kafka: {e}")
        return

    # 2. Lectura de la fuente de la verdad (Dataset Físico)
    try:
        print(f"Cargando dataset clínico desde: {RECORD_PATH}")
        record = wfdb.rdrecord(RECORD_PATH)
        signals = record.p_signal[:, 0]  # Extraer primera derivación (Canal 1)
    except Exception as e:
        print(f"Error leyendo archivo MIT-BIH: {e}")
        return

    print("Iniciando transmisión de telemetría ininterrumpida...")
    
    # 3. Generación de Flujo Continuo
    while True:
        for value in signals:
            payload = {
                "patient_id": patient_id,
                "ecg_value": float(value),
                "timestamp": datetime.now().isoformat()
            }
            
            # Envío al stream
            producer.send(TOPIC_NAME, payload)
            
            # Retraso para simular la frecuencia de muestreo del sensor en tiempo real
            time.sleep(0.01) 
            
        # Al terminar el archivo, el bucle reinicia para mantener vivo el flujo continuo
        print("[DATA SOURCE] Fin del archivo. Reiniciando ciclo de transmisión...")

if __name__ == "__main__":
    # Permite ejecutar fácilmente la instancia por defecto
    run_sensor()
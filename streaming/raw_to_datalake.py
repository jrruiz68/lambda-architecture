"""
=========================================================
INGESTOR AL DATA LAKE (MASTER DATASET)
=========================================================
Este módulo asegura la persistencia inmutable de los datos crudos.

- Implementa la política 'earliest' para evitar la pérdida de datos.
- Garantiza que el Master Dataset sea íntegro, permitiendo reprocesar
  el historial completo si la lógica de negocio cambia.
"""

import json
import os
from datetime import datetime
from kafka import KafkaConsumer
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# --- CONFIGURACIÓN EXTERNALIZADA ---
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC_INPUT = os.getenv("KAFKA_TOPIC_RAW", "ecg_raw")
DATALAKE_BASE = 'data/datalake'

def run_datalake_ingestion():
    print(f"[DATA LAKE] Iniciando ingesta persistente desde {KAFKA_BROKER}...")
    
    try:
        # CONFIGURACIÓN CRÍTICA: auto_offset_reset='earliest'
        # Esto asegura que no perdamos datos si el consumidor se desconecta temporalmente.
        consumer = KafkaConsumer(
            TOPIC_INPUT,
            bootstrap_servers=[KAFKA_BROKER],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',  # <--- CAMBIO CLAVE 
            enable_auto_commit=True,       # Mantiene el rastro de qué se ha leído
            group_id='datalake-group'      # Identificador para recordar el progreso
        )
    except Exception as e:
        print(f"Error conectando a Kafka: {e}")
        return

    print(f"Guardando datos en el Master Dataset ({DATALAKE_BASE})...")

    for message in consumer:
        data = message.value
        
        # Particionado por día (Buenas prácticas de Data Lake)
        today_str = datetime.now().strftime('%Y-%m-%d')
        day_folder = os.path.join(DATALAKE_BASE, today_str)
        os.makedirs(day_folder, exist_ok=True)

        file_path = os.path.join(day_folder, 'raw_ecg.jsonl')

        # Escritura Append-Only
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data) + '\n')

if __name__ == "__main__":
    run_datalake_ingestion()
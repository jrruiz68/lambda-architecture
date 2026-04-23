import json
import os
from datetime import datetime
from kafka import KafkaConsumer

# --- CONFIGURACIÓN ---
KAFKA_BROKER = 'localhost:9092'
TOPIC_INPUT = 'ecg_raw'
DATALAKE_BASE = 'data/datalake' # Aquí se guardarán los archivos crudos

def run_datalake_ingestion():
    print(f"🌊 Iniciando Ingesta al Data Lake conectando a {KAFKA_BROKER}...")
    
    # Nos conectamos a Kafka
    consumer = KafkaConsumer(
        TOPIC_INPUT,
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='latest'
    )

    print("Data Lake Activo. Guardando datos crudos...")

    for message in consumer:
        data = message.value
        
        # 1. Crear la estructura de carpetas por día (Particionado del Data Lake)
        # Ejemplo: data/datalake/2026-04-22/
        today_str = datetime.now().strftime('%Y-%m-%d')
        day_folder = os.path.join(DATALAKE_BASE, today_str)
        os.makedirs(day_folder, exist_ok=True)

        # 2. Archivo donde se guardarán los datos de hoy (JSON Lines)
        file_path = os.path.join(day_folder, 'raw_ecg.jsonl')

        # 3. Escribir el dato crudo
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data) + '\n')

if __name__ == "__main__":
    run_datalake_ingestion()
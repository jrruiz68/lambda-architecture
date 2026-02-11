import time
import json
import wfdb
import numpy as np
from kafka import KafkaProducer

# CONFIGURACIÓN
# Apuntamos a localhost:9092 porque estamos ejecutando este script 
# desde TU máquina (hacia el contenedor Docker)
KAFKA_BROKER = 'localhost:9092'
TOPIC_NAME = 'ecg_raw'
DATA_PATH = 'data/raw/100'  # Ruta al archivo (sin extensión)

def run_producer():
    print(f"🏥 Iniciando simulador de sensor cardíaco conectado a {KAFKA_BROKER}...")
    
    # 1. Configurar el Productor de Kafka
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode('utf-8') # Convertir dict a JSON bytes
    )

    # 2. Leer el archivo médico real (Formato WFDB)
    # Esto lee el archivo 100.dat y 100.hea
    try:
        record = wfdb.rdrecord(DATA_PATH)
        print(f"✅ Datos del paciente cargados: {record.record_name}")
        print(f"   Frecuencia de muestreo: {record.fs} Hz (muestras por segundo)")
        print(f"   Longitud de señal: {record.sig_len} muestras")
    except FileNotFoundError:
        print("❌ ERROR: No encuentro los archivos 100.dat/100.hea en data/raw/")
        return

    # La señal ECG suele tener 2 canales. Usaremos solo el canal 0 (MLII)
    ecg_signal = record.p_signal[:, 0]
    
    # 3. Bucle de transmisión (Streaming)
    # Simulamos tiempo real enviando datos a la velocidad que se grabaron (360 Hz)
    frecuencia_muestreo = record.fs
    tiempo_espera = 1.0 / frecuencia_muestreo  # Ej: 1/360 = 0.0027 segundos
    
    patient_id = "PACIENTE-100"
    
    print("🚀 Transmitiendo signos vitales a Kafka...")
    
    for i, valor_ecg in enumerate(ecg_signal):
        # Crear el mensaje JSON
        mensaje = {
            "patient_id": patient_id,
            "timestamp": time.time(),     # Hora actual
            "sample_index": i,            # Índice original del archivo
            "ecg_value": float(valor_ecg) # Valor del voltaje del corazón
        }
        
        # Enviar a Kafka
        producer.send(TOPIC_NAME, mensaje)
        
        # Simular velocidad real (imprimir cada 100 muestras para no ensuciar la consola)
        if i % 360 == 0:
            print(f"   --> Enviando segundo {i // 360}: Valor {valor_ecg:.3f}")
            
        time.sleep(tiempo_espera) # Esperar para imitar el ritmo del corazón real

    print("🏁 Fin de la grabación.")
    producer.close()

if __name__ == "__main__":
    run_producer()
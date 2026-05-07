import json
import os
import psycopg2
from datetime import datetime
import pandas as pd

from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# --- CONFIGURACIÓN ---
POSTGRES_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "medical_iot"),
    "user": os.getenv("DB_USER", "admin"),
    "password": os.getenv("DB_PASSWORD", "admin")
}
DATALAKE_BASE = os.getenv("DATALAKE_PATH", 'data/datalake')

def run_batch_processor(target_date_str=None):
    # Si no le pasamos fecha, procesa el día de hoy
    if target_date_str is None:
        target_date_str = datetime.now().strftime('%Y-%m-%d')

    print(f"Iniciando Capa Batch para el día: {target_date_str}...")

    day_folder = os.path.join(DATALAKE_BASE, target_date_str)
    file_path = os.path.join(day_folder, 'raw_ecg.jsonl')

    if not os.path.exists(file_path):
        print(f"No hay datos en el Data Lake para la fecha {target_date_str}")
        return

    # 1. Leer TODOS los datos del Data Lake (Heavy lifting)
    print("Leyendo datos crudos del Data Lake...")
    records = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            records.append(json.loads(line))

    df = pd.DataFrame(records)
    print(f"Procesando {len(df)} registros...")

    # 2. Calcular métricas (Agregación Batch)
    # Por cada paciente, calculamos su resumen del día
    resumen = df.groupby('patient_id').agg(
        total_muestras=('ecg_value', 'count'),
        promedio_ecg=('ecg_value', 'mean'),
        max_ecg=('ecg_value', 'max'),
        min_ecg=('ecg_value', 'min')
    ).reset_index()

    # 3. Guardar la "Verdad Absoluta" en PostgreSQL (Serving Layer)
    print("Guardando resultados agregados en PostgreSQL...")
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    cur = conn.cursor()

    # Creamos la tabla si no existe
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vitals_daily_batch (
            fecha DATE,
            patient_id VARCHAR(50),
            total_muestras INT,
            promedio_ecg FLOAT,
            max_ecg FLOAT,
            min_ecg FLOAT,
            PRIMARY KEY (fecha, patient_id)
        );
    """)

    # Insertamos (o actualizamos) los datos del día
    for _, row in resumen.iterrows():
        cur.execute("""
            INSERT INTO vitals_daily_batch (fecha, patient_id, total_muestras, promedio_ecg, max_ecg, min_ecg)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (fecha, patient_id)
            DO UPDATE SET
                total_muestras = EXCLUDED.total_muestras,
                promedio_ecg = EXCLUDED.promedio_ecg,
                max_ecg = EXCLUDED.max_ecg,
                min_ecg = EXCLUDED.min_ecg;
        """, (target_date_str, row['patient_id'], row['total_muestras'], row['promedio_ecg'], row['max_ecg'], row['min_ecg']))

    conn.commit()
    conn.close()
    print("Capa Batch finalizada con éxito. Datos listos para Serving.")

if __name__ == "__main__":
    run_batch_processor()
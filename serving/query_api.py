"""
=========================================================
CAPA DE SERVING (QUERY API)
=========================================================
Este módulo representa la Serving Layer explícita de la Arquitectura Lambda.

- Separa la capa de almacenamiento de la de visualización.
- Expone los datos procesados (tanto en streaming como en batch) a través 
  de una API RESTful.
- Demuestra cómo las aplicaciones cliente pueden consultar la vista 
  Real-time (Speed) y la vista Histórica (Batch).
"""

from fastapi import FastAPI, HTTPException
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date
import os
from dotenv import load_dotenv

# Cargar variables de entorno del archivo .env
load_dotenv()

app = FastAPI(
    title="Medical IoT - Lambda Query API",
    description="Serving Layer para la Arquitectura Lambda",
    version="1.0.0"
)

# --- CONFIGURACIÓN DE BASE DE DATOS ---
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "medical_iot"),
    "user": os.getenv("DB_USER", "admin"),
    "password": os.getenv("DB_PASSWORD", "admin")
}

def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error de conexión a BD: {str(e)}")

@app.get("/")
def root():
    return {"mensaje": "Serving Layer Activa. Visita /docs para ver la interfaz Swagger."}

@app.get("/realtime")
def get_realtime_view(limit: int = 50):
    """
    Vista de la Speed Layer: Trae las anomalías detectadas en tiempo real.
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Consulta a la tabla gestionada por anomaly_detector.py
        cur.execute(
            "SELECT * FROM cardiac_anomalies ORDER BY timestamp DESC LIMIT %s", 
            (limit,)
        )
        records = cur.fetchall()
        return {"source": "Speed Layer", "count": len(records), "data": records}
    finally:
        cur.close()
        conn.close()

@app.get("/batch")
def get_batch_view(limit: int = 10):
    """
    Vista de la Batch Layer: Resúmenes diarios procesados históricamente.
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Consulta a la tabla gestionada por batch_daily_processor.py
        cur.execute(
            "SELECT * FROM vitals_daily_batch ORDER BY fecha DESC LIMIT %s", 
            (limit,)
        )
        records = cur.fetchall()
        return {"source": "Batch Layer", "count": len(records), "data": records}
    except Exception as e:
        # Previene errores si la tabla aún no se ha creado
        return {"source": "Batch Layer", "error": str(e), "data": []}
    finally:
        cur.close()
        conn.close()

@app.get("/summary")
def get_summary():
    """
    Resumen rápido del estado del sistema uniendo ambas capas.
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT COUNT(*) as total FROM cardiac_anomalies WHERE is_anomaly = true")
        anomalias = cur.fetchone()['total']
        
        # Usamos un try/except interno por si el batch aún no ha corrido
        try:
            cur.execute("SELECT COUNT(*) as total FROM vitals_daily_batch")
            dias_procesados = cur.fetchone()['total']
        except:
            dias_procesados = 0
            
        return {
            "status": "healthy",
            "total_anomalies_detected_realtime": anomalias,
            "total_batch_days_processed": dias_procesados
        }
    except Exception as e:
         return {"status": "error", "detail": str(e)}
    finally:
        cur.close()
        conn.close()

@app.get("/unified/{patient_id}")
def get_unified_view(patient_id: str):
    """
    =========================================================
    VISTA UNIFICADA (MERGE) - ARQUITECTURA LAMBDA
    =========================================================
    Demuestra el principio clave de Lambda:
    Precisión (Batch) + Inmediatez (Speed)
    
    Une el historial de vitals_daily_batch con los eventos 
    recientes de cardiac_anomalies para dar una vista clínica 360.
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # 1. BATCH VIEW (Precisión Histórica)
        # Obtenemos los últimos 7 días procesados para ver la tendencia del paciente.
        cur.execute("""
            SELECT fecha, total_muestras, promedio_ecg, max_ecg, min_ecg 
            FROM vitals_daily_batch 
            WHERE patient_id = %s 
            ORDER BY fecha DESC LIMIT 7
        """, (patient_id,))
        batch_history = cur.fetchall()

        # 2. REAL-TIME VIEW (Inmediatez / Speed Layer)
        # Obtenemos solo las anomalías críticas detectadas el DÍA DE HOY.
        today_str = date.today().isoformat()
        cur.execute("""
            SELECT timestamp, ecg_value 
            FROM cardiac_anomalies 
            WHERE patient_id = %s 
              AND is_anomaly = true 
              AND DATE(timestamp) = %s
            ORDER BY timestamp DESC LIMIT 20
        """, (patient_id, today_str))
        realtime_alerts = cur.fetchall()

        # 3. MERGE (La fusión de ambas capas)
        unified_response = {
            "patient_id": patient_id,
            "architecture_principle": "Lambda Merge (Batch Precision + Speed Immediacy)",
            "clinical_view": {
                "historical_trend_batch": batch_history,
                "critical_alerts_today_speed": realtime_alerts
            }
        }
        
        return unified_response
        
    except Exception as e:
        return {"status": "error", "detail": str(e)}
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    import uvicorn
    # Se ejecuta en el puerto 8000 por defecto
    uvicorn.run(app, host="0.0.0.0", port=8000)
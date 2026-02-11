import wfdb
import numpy as np
import mlflow
import mlflow.sklearn
from sklearn.ensemble import IsolationForest

# --- CONFIGURACIÓN ---
DATA_PATH = 'data/raw/100'  # Ruta local al archivo 100.dat
MLFLOW_URI = "http://localhost:5000"
EXPERIMENT_NAME = "Deteccion_Arritmias_ECG"

def train():
    print("🧠 Iniciando entrenamiento del modelo...")
    
    # 1. Conectar con MLflow (que está corriendo en Docker)
    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    # 2. Cargar datos históricos (Simulamos que son datos "sanos" para entrenar)
    try:
        record = wfdb.rdrecord(DATA_PATH)
        signal = record.p_signal[:, 0] # Usamos solo el canal 0
        print(f"   Datos cargados: {len(signal)} puntos de señal.")
    except Exception as e:
        print(f"❌ Error cargando datos: {e}")
        return

    # 3. Preprocesamiento: Cortar la señal en ventanas pequeñas
    # (El modelo analizará trozos de 100 muestras a la vez)
    window_size = 100
    # Recortamos para que sea divisible por el tamaño de ventana
    limit = (len(signal) // window_size) * window_size
    X = signal[:limit].reshape(-1, window_size)
    
    print(f"   Entrenando con {X.shape[0]} ventanas de señal...")

    # 4. Iniciar carrera en MLflow
    with mlflow.start_run(run_name="Entrenamiento_Base_IsolationForest"):
        # Definir parámetros del modelo
        contamination = 0.01  # Esperamos 1% de anomalías
        model = IsolationForest(contamination=contamination, random_state=42)
        
        # Entrenar
        model.fit(X)
        
        # Registrar métricas y parámetros
        mlflow.log_param("window_size", window_size)
        mlflow.log_param("contamination", contamination)
        mlflow.log_param("model_type", "IsolationForest")
        
        # Guardar el modelo en el registro de modelos de MLflow
        mlflow.sklearn.log_model(model, "model_ecg")
        
        print("✅ Modelo entrenado y enviado a MLflow exitosamente.")
        print(f"   ID del Experimento: {mlflow.active_run().info.run_id}")

if __name__ == "__main__":
    train()
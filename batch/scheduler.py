"""
=========================================================
AUTOMATIZACIÓN DE LA CAPA BATCH (SCHEDULER)
=========================================================
Este módulo actúa como el orquestador temporal de la Arquitectura Lambda.

- Demuestra que la Batch Layer no procesa datos evento por evento (como la Speed Layer),
  sino que se ejecuta periódicamente (ej. una vez al día a la medianoche).
- Procesa bloques completos de datos históricos (Data Lake) para consolidar
  la Verdad Absoluta en la Serving Layer.
"""

import time
import subprocess
import sys
import os

# --- CONFIGURACIÓN DEL SCHEDULER ---
# Para un entorno de producción hospitalario, esto suele ser a las 00:00.
# Para esta demostración, lo configuraremos para que procese cada X segundos/minutos.
INTERVALO_SEGUNDOS = 60  # Ejecutar cada 60 segundos para facilitar la demostración

def ejecutar_batch_processor():
    print("\n" + "="*50)
    print("[SCHEDULER] Iniciando ejecución periódica de la Capa Batch...")
    print("="*50)
    
    # Ruta al script que hace el procesamiento pesado
    script_path = os.path.join(os.path.dirname(__file__), 'batch_daily_processor.py')
    
    try:
        # Ejecutamos el procesador diario como un subproceso
        resultado = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True
        )
        
        # Mostramos la salida del script Batch
        if resultado.stdout:
            print(resultado.stdout)
        if resultado.stderr:
            print(f"[WARNING/ERROR]:\n{resultado.stderr}")
            
        print("[SCHEDULER] Procesamiento histórico completado. Esperando siguiente ciclo...")
        
    except Exception as e:
        print(f"[SCHEDULER] Error al ejecutar el script batch: {e}")

def iniciar_scheduler():
    print(f"Scheduler iniciado. El procesamiento Batch se ejecutará cada {INTERVALO_SEGUNDOS} segundos.")
    print("Presiona Ctrl+C para detener.")
    
    # Ejecutamos la primera vez inmediatamente para que el estudiante vea el resultado
    ejecutar_batch_processor()
    
    # Ciclo infinito de automatización
    try:
        while True:
            time.sleep(INTERVALO_SEGUNDOS)
            ejecutar_batch_processor()
    except KeyboardInterrupt:
        print("\nScheduler detenido manualmente.")

if __name__ == "__main__":
    iniciar_scheduler()
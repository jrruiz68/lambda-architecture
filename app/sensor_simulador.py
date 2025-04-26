import json
import time
from kafka import KafkaProducer
from faker import Faker

fake = Faker()

producer = KafkaProducer(
    bootstrap_servers='kafka:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

while True:
    patient_id = fake.uuid4()[:6]  # ID corto para simulación
    timestamp = int(time.time() * 1000)  # Timestamp en milisegundos
    heart_rate = fake.random_int(min=60, max=120)  # Pulsaciones por minuto
    oxygen = fake.random_int(min=88, max=100)  # Saturación de oxígeno
    systolic = fake.random_int(min=90, max=180)  # Presión arterial sistólica
    diastolic = fake.random_int(min=60, max=120)  # Diastólica

    message = {
        "patient_id": f"P-{patient_id}",
        "timestamp": timestamp,
        "heart_rate": heart_rate,
        "oxygen": oxygen,
        "blood_pressure": f"{systolic}/{diastolic}"
    }
    
    producer.send('patient_vitals', message)
    time.sleep(1)  # Envía un mensaje por segundo
import time
import random
import json

def generate_sensor_data():
    return {
        "timestamp": time.time(),
        "machine_id": f"M-{random.randint(1, 5)}",
        "temperature": round(random.uniform(60, 120), 2),
        "vibration": round(random.uniform(0.1, 3.0), 2),
        "load": round(random.uniform(0.0, 1.0), 2)
    }

while True:
    data = generate_sensor_data()
    print(json.dumps(data))
    time.sleep(random.uniform(0.2, 1.0))  # Vary rate to simulate load

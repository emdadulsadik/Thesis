import os
import time
import random
import paho.mqtt.client as mqtt
import json

machine_id = os.getenv("MACHINE_ID", "machine-unknown")
broker_host = os.getenv("MQTT_BROKER", "localhost")
interval = float(os.getenv("INTERVAL", 1.0))

client = mqtt.Client()
client.connect(broker_host, 1883, 60)
client.loop_start()

while True:
    data = {
        "temperature": round(random.uniform(60, 100), 2),
        "vibration": round(random.uniform(0.2, 1.5), 3),
        "load": round(random.uniform(10, 80), 2)
    }

    topic = f"data/{machine_id}"
    client.publish(topic, json.dumps(data))
    print(f"[SIM] {machine_id} => {data}")
    time.sleep(interval)

import os, time, random
from kubernetes import client, config
from paho.mqtt.client import Client
from paho.mqtt.enums import CallbackAPIVersion

broker = os.getenv("MQTT_BROKER", "mqtt-broker")
mqtt_client = Client(callback_api_version=CallbackAPIVersion.VERSION2)
mqtt_client.connect(broker, 1883, 60)

config.load_incluster_config()
apps_v1 = client.AppsV1Api()

DEPLOYMENT_NAME = "machine-iot-sim"
NAMESPACE = "default"

def scale_deployment(new_replicas):
    body = {"spec": {"replicas": new_replicas}}
    apps_v1.patch_namespaced_deployment_scale(
        name=DEPLOYMENT_NAME, namespace=NAMESPACE, body=body)
    print(f"[AI-SCHED] Scaled {DEPLOYMENT_NAME} to {new_replicas} replicas")

while True:
    simulated_load = random.randint(1, 100)
    print(f"[AI-SCHED] Simulated load: {simulated_load}")

    if simulated_load > 70:
        scale_deployment(5)
        mqtt_client.publish("control/simulator", "High load detected — scaled to 5 replicas")
    else:
        scale_deployment(3)
        mqtt_client.publish("control/simulator", "Normal load — scaled to 3 replicas")

    time.sleep(30)

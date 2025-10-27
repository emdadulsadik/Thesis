import os, json, time
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from collections import deque, defaultdict
import logging

logging.basicConfig(level=logging.INFO)

broker = os.getenv("MQTT_BROKER", "mqtt-broker")
client_id = os.getenv("CLIENT_ID", "processor")
MAXLEN = int(os.getenv("MAXLEN", "50"))

buffers = defaultdict(lambda: deque(maxlen=MAXLEN))
assigned = set()

def on_message(client, userdata, msg):
    topic = msg.topic
    if topic.startswith("control/"):
        payload = json.loads(msg.payload)
        if "assign" in payload:
            for machine_id in payload["assign"]:
                assigned.add(machine_id)
                client.subscribe(f"data/{machine_id}")
                client.subscribe(f"state/{machine_id}")
                logging.info(f"[{client_id}] Assigned {machine_id}")
    elif topic.startswith("state/"):
        machine_id = topic.split("/")[-1]
        buffers[machine_id] = deque(json.loads(msg.payload), maxlen=MAXLEN)
        logging.info(f"[{client_id}] Hydrated buffer for {machine_id}")
    elif topic.startswith("data/"):
        machine_id = topic.split("/")[-1]
        payload = json.loads(msg.payload)
        buffers[machine_id].append(payload)
        logging.info(f"[{client_id}] Ingested {machine_id}: {payload}")

client = mqtt.Client(CallbackAPIVersion.VERSION2, client_id)
client.on_message = on_message
client.connect(broker, 1883, 60)
client.subscribe("control/#")
client.loop_start()

while True:
    logging.info(f"[MACHINE-PROCESSOR]")
    for machine_id in assigned:
        buf = buffers[machine_id]
        if buf:
            avg_temp = sum(x["temperature"] for x in buf) / len(buf)
            logging.info(f"[{client_id}] {machine_id} → avg temp: {avg_temp:.2f}")
    time.sleep(2)

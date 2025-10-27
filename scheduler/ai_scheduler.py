import time, json, os
from collections import defaultdict, deque
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import logging

logging.basicConfig(level=logging.INFO)
broker = os.getenv("MQTT_BROKER", "mqtt-broker")
WINDOW = 30  # seconds
RATE_THRESHOLD = 15  # messages per window

message_counts = defaultdict(lambda: deque(maxlen=WINDOW))
assignments = {"processor1": set(), "processor2": set()}

client = mqtt.Client(CallbackAPIVersion.VERSION2)

def on_message(client, userdata, msg):
    machine_id = msg.topic.split("/")[-1]
    message_counts[machine_id].append(time.time())
    logging.info(f"[AI-SCHED] received msg. machine: {machine_id}, msg: {msg}")

def get_rate(machine_id):
    now = time.time()
    timestamps = message_counts[machine_id]
    return len([t for t in timestamps if now - t <= WINDOW])

def assign(machine_id, processor_id):
    payload = {"assign": [machine_id]}
    topic = f"control/{processor_id}"
    client.publish(topic, json.dumps(payload), retain=True)
    logging.info(f"[AI] Assigned {machine_id} to {processor_id}")
    assignments[processor_id].add(machine_id)

client.on_message = on_message
client.connect(broker, 1883, 60)
client.subscribe(f"data/#")
client.loop_start()

while True:
    logging.info(f"[AI-SCHED]")
    for m_id in message_counts.keys():
        rate = get_rate(m_id)
        logging.info(f"[AI] {m_id} rate = {rate} msg/min")
        if rate > RATE_THRESHOLD and m_id not in assignments["processor2"]:
            assign(m_id, "processor2")
    time.sleep(5)
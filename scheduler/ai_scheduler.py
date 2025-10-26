import os, time, random, json
from collections import defaultdict, deque
from kubernetes import client as k8sClient, config as k8sConfig
from paho.mqtt.client import Client
from paho.mqtt.enums import CallbackAPIVersion


WINDOW = 30  # seconds
RATE_THRESHOLD = 15  # messages per window

message_counts = defaultdict(lambda: deque(maxlen=WINDOW))
# todo: assignments should also be in the mqtt so that in case scheduler restarts it can resume.
assignments = {"processor1": set(), "processor2": set()}

broker = os.getenv("MQTT_BROKER", "mqtt-broker")
mqtt_client = Client(callback_api_version=CallbackAPIVersion.VERSION2)
mqtt_client.connect(broker, 1883, 60)


# message_counts = { machine_id_1: [timestamp_1, timestamp_2, timestamp_N], machine_id_2: [..], ...}
def on_message(client, userdata, msg):
    machine_id = msg.topic.split("/")[-1]
    message_counts[machine_id].append(time.time())

mqtt_client.on_message = on_message
mqtt_client.connect(broker, 1883, 60)

for i in range(1, 6):
    mqtt_client.subscribe(f"data/machine-{i}")
mqtt_client.loop_start()

def get_rate(machine_id):
    now = time.time()
    timestamps = message_counts[machine_id]
    return len([t for t in timestamps if now - t <= WINDOW])

def assign(machine_id, processor_id):
    payload = {"assign": [machine_id]}
    topic = f"control/{processor_id}"
    mqtt_client.publish(topic, json.dumps(payload), retain=True)
    print(f"[AI-SCHED] Assigned {machine_id} to {processor_id}")
    assignments[processor_id].add(machine_id)

def ai_scheduler_loop():
    while True:
        for machine_id in message_counts.keys():
            rate = get_rate(machine_id)
            print(f"[AI-SCHED] {machine_id} rate = {rate} msg/min")
            if rate > RATE_THRESHOLD and machine_id not in assignments["processor2"]:
                print(f"[AI-SCHED] rate = {rate} msg/min is bigger than the {RATE_THRESHOLD}.")
                assign(machine_id, "processor2")
        time.sleep(5)

ai_scheduler_loop()
import time, json
from collections import defaultdict, deque
import paho.mqtt.client as mqtt

MQTT_BROKER = "mqtt-broker"
WINDOW = 30  # seconds
RATE_THRESHOLD = 15  # messages per window

message_counts = defaultdict(lambda: deque(maxlen=WINDOW))
assignments = {"processor1": set(), "processor2": set()}

client = mqtt.Client()

def on_message(client, userdata, msg):
    machine_id = msg.topic.split("/")[-1]
    message_counts[machine_id].append(time.time())

client.on_message = on_message
client.connect(MQTT_BROKER, 1883, 60)
for i in range(1, 6):
    client.subscribe(f"data/machine{i}")
client.loop_start()

def get_rate(machine_id):
    now = time.time()
    timestamps = message_counts[machine_id]
    return len([t for t in timestamps if now - t <= WINDOW])

def assign(machine_id, processor_id):
    payload = {"assign": [machine_id]}
    topic = f"control/{processor_id}"
    client.publish(topic, json.dumps(payload), retain=True)
    print(f"[AI] Assigned {machine_id} to {processor_id}")
    assignments[processor_id].add(machine_id)

def ai_scheduler_loop():
    while True:
        for m_id in message_counts.keys():
            rate = get_rate(m_id)
            print(f"[AI] {m_id} rate = {rate} msg/min")
            if rate > RATE_THRESHOLD and m_id not in assignments["processor2"]:
                assign(m_id, "processor2")
        time.sleep(5)

ai_scheduler_loop()

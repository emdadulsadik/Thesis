import os, json, time
from paho.mqtt.client import Client
from paho.mqtt.enums import CallbackAPIVersion
from collections import deque, defaultdict

broker = os.getenv("MQTT_BROKER", "localhost")
client_id = os.getenv("CLIENT_ID", "processor") #machine-processor
MAXLEN = int(os.getenv("MAXLEN", "50"))

buffers = defaultdict(lambda: deque(maxlen=MAXLEN))
assigned_machines = set()

# This machine starts by receiving control messages, upon receiving control message it subscribes to data and state topics.
# Upon receiving messages from state and data topic, it fills up the buffer for its machine_id.
# Then when you new machine is launched, it gets the control message and ends up reading from the buffer.
# But for a new machine there is no buffer, there needs to be a handover. AI scheduler should do that?

def on_message(client, userdata, msg):
    topic = msg.topic
    if topic.startswith("control/"):
        payload = json.loads(msg.payload)
        if "assign" in payload:
            for machine_id in payload["assign"]:
                assigned_machines.add(machine_id)
                client.subscribe(f"data/machine-{machine_id}")
                client.subscribe(f"state/machine-{machine_id}")
                print(f"[{client_id}] Assigned {machine_id}")
    elif topic.startswith("state/"):
        machine_id = topic.split("/")[-1]
        payload = json.loads(msg.payload)
        buffers[machine_id] = deque(payload, maxlen=MAXLEN)
        print(f"[{client_id}] Hydrated buffer for {machine_id}: {payload}")
    elif topic.startswith("data/"):
        machine_id = topic.split("/")[-1]
        payload = json.loads(msg.payload)
        buffers[machine_id].append(payload)
        print(f"[{client_id}] Ingested {machine_id}: {payload}")

client = Client(CallbackAPIVersion.VERSION2, client_id)
client.on_message = on_message
client.connect(broker, 1883, 60)
client.subscribe("control/#")
client.loop_start()

while True:
    for machine_id in assigned_machines:
        buf = buffers[machine_id]
        if buf:
            avg_temp = sum(x["temperature"] for x in buf) / len(buf)
            print(f"[{client_id}] {machine_id} → avg temp: {avg_temp:.2f}")
    time.sleep(2)

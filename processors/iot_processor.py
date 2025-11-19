import os,json,time,threading,statistics,logging,sys, random
import paho.mqtt.client as mqtt
from collections import deque
import psutil
from paho.mqtt.enums import CallbackAPIVersion

logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
    format='%(asctime)s - %(levelname)s - %(message)s'
)

BROKER = os.getenv("MQTT_BROKER", "mqtt-broker")
PROCESSOR_ID = os.getenv("CLIENT_ID")
DATA_TOPIC = "data/#"  # subscribe to all IoT simulator topics
STATE_TOPIC = f"state/{PROCESSOR_ID}"
BUFFER_TOPIC = f"buffer/{PROCESSOR_ID}"
METRICS_TOPIC = f"metrics/{PROCESSOR_ID}"
MAXLEN = int(os.getenv("MAXLEN", "30"))
STATE_INTERVAL = 5  # seconds
ASSIGNED_MACHINES = os.getenv(f"ASSIGNED_MACHINES_{PROCESSOR_ID.replace('-', '_')}", "").split(",")

buffer = deque(maxlen=MAXLEN)
metrics = {"processed": 0, "avg_rate": 0.0, "avg_latency": 0.0}
processing_times = deque(maxlen=MAXLEN)
last_publish_time = time.time()

mqtt_client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2, client_id=PROCESSOR_ID)

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logging.info(f"[{PROCESSOR_ID}] Connected to MQTT broker at {BROKER}")
        client.subscribe(DATA_TOPIC)
    else:
        logging.info(f"[{PROCESSOR_ID}] Connection failed with code {rc}")

def on_message(client, userdata, msg):
    global last_publish_time
    start_time = time.time()
    payload = msg.payload.decode()
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        data = {"raw": payload}

    # Simulate processing workload
    time.sleep(random.uniform(0.05, 0.15))

    buffer.append(data)
    processing_times.append(time.time() - start_time)
    metrics["processed"] += 1

    now = time.time()
    if now - last_publish_time >= STATE_INTERVAL:
        publish_all()
        last_publish_time = now

def publish_all():
    """Publish buffer, metrics, and state JSON messages."""
    if not buffer:
        return

    cpu_usage = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    avg_latency = statistics.mean(processing_times) if processing_times else 0
    avg_rate = metrics["processed"] / (time.time() - start_time_global + 1e-6)

    buffer_payload = {
        "processor_id": PROCESSOR_ID,
        "timestamp": time.time(),
        "buffer_size": len(buffer),
        "buffer_capacity": MAXLEN,
        "assigned_machines": ASSIGNED_MACHINES,
    }

    metrics_payload = {
        "processor_id": PROCESSOR_ID,
        "timestamp": time.time(),
        "avg_latency": round(avg_latency, 4),
        "avg_rate": round(avg_rate, 2),
        "cpu_usage": cpu_usage,
        "mem_usage": round(mem.percent, 2),
        "assigned_machines": ASSIGNED_MACHINES,
    }

    # Merge both into a combined state payload
    state_payload = {**buffer_payload, **metrics_payload}

    mqtt_client.publish(BUFFER_TOPIC, json.dumps(buffer_payload))
    mqtt_client.publish(METRICS_TOPIC, json.dumps(metrics_payload))
    mqtt_client.publish(STATE_TOPIC, json.dumps(state_payload))

    logging.info(f"[{PROCESSOR_ID}] Published buffer: {buffer_payload}")
    logging.info(f"[{PROCESSOR_ID}] Published metrics: {metrics_payload}")

def state_publisher_loop():
    """Background thread to publish state even when no new data arrives."""
    while True:
        time.sleep(STATE_INTERVAL)
        publish_all()

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

logging.info(f"[{PROCESSOR_ID}] Starting processor; connecting to {BROKER} ...")
mqtt_client.connect(BROKER, 1883, 60)

# Track uptime for average rate calculation
start_time_global = time.time()

# Start background thread for periodic publishing
threading.Thread(target=state_publisher_loop, daemon=True).start()

mqtt_client.loop_forever()

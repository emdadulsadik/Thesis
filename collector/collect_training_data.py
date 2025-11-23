import os, time, json, csv, sys, logging
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)

MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
DATA_DIR = "/data"
CSV_FILE = os.path.join(DATA_DIR, "features.csv")
JSONL_FILE = os.path.join(DATA_DIR, "raw_events.jsonl")

processor_state = {}


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def write_csv(record):
    """Append record to CSV, creating header if missing."""
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, "a", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=record.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(record)


def write_jsonl(record):
    """Append event to raw_events.jsonl for temporal analysis."""
    with open(JSONL_FILE, "a") as f:
        json.dump(record, f)
        f.write("\n")


def merge_state(processor_id, update):
    """Merge partial updates and write FULL feature snapshot."""

    base = {
        "timestamp": time.time(),
        "processor_id": processor_id,
        "cpu_usage": 0.0,
        "mem_usage": 0.0,
        "buffer_size": 0,
        "buffer_capacity": 0,
        "avg_latency": 0.0,
        "avg_rate": 0.0,
        "temperature": 0.0,
        "vibration": 0.0,
        "load": 0.0,
        "assigned_machines": []
    }

    # Load last known state or base
    current = processor_state.get(processor_id, base.copy())

    # Apply update
    current.update(update)

    # ALWAYS refresh timestamp
    current["timestamp"] = time.time()

    # Save state
    processor_state[processor_id] = current

    clean_state = sanitize_state(current.copy())

    # Write FULL snapshot, not partial update
    write_csv(clean_state)
    write_jsonl(clean_state)


def on_message(client, userdata, msg):
    topic = msg.topic
    try:
        payload = json.loads(msg.payload.decode())
    except Exception as e:
        logging.info(f"[Collector] Invalid JSON from {topic}: {e}")
        return

    processor_id = payload.get("processor_id", "unknown")

    if topic.startswith("metrics/"):
        merge_state(
            processor_id,
            {
                "cpu_usage": payload.get("cpu_usage", 0.0),
                "mem_usage": payload.get("mem_usage", 0.0),
                "avg_latency": payload.get("avg_latency", 0.0),
                "avg_rate": payload.get("avg_rate", 0.0),
                "assigned_machines": payload.get("assigned_machines", []),
            },
        )
    elif topic.startswith("buffer/"):
        merge_state(
            processor_id,
            {
                "buffer_size": payload.get("buffer_size", 0),
                "buffer_capacity": payload.get("buffer_capacity", 0),
                "assigned_machines": payload.get("assigned_machines", []),
            },
        )
    elif topic.startswith("data/") or topic.startswith("state/"):
        merge_state(processor_id, payload)
    else:
        logging.info(f"[Collector] Ignored unknown topic: {topic}")


def sanitize_state(d):
    for k, v in d.items():
        if isinstance(v, list):
            continue
        if v is None:
            d[k] = 0.0
        elif isinstance(v, str):
            try:
                d[k] = float(v)
            except:
                d[k] = 0.0
    return d

def on_connect(client, userdata, flags, rc, properties=None):
    logging.info(f"[Collector] Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
    client.subscribe("metrics/#")
    client.subscribe("buffer/#")
    client.subscribe("data/#")
    client.subscribe("state/#")


if __name__ == "__main__":
    ensure_data_dir()

    client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    logging.info(f"[Collector] Connecting to {MQTT_BROKER}:{MQTT_PORT}")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

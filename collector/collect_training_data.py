import os, time, json, csv, logging
from collections import defaultdict, deque
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

BROKER = os.getenv("MQTT_BROKER", "mqtt-broker")
OUT_RAW = os.getenv("OUT_RAW", "raw_events.jsonl")
OUT_FEATURES = os.getenv("OUT_FEATURES", "features.csv")
WINDOW = int(os.getenv("WINDOW", "30"))  # seconds for feature window
HORIZON = int(os.getenv("HORIZON", "60"))  # seconds to label ahead (overload within H)

# data structures
# per machine stream of timestamps or per-processor metrics
msg_times = defaultdict(list)  # machine_id -> list of arrival timestamps
buffer_sizes = defaultdict(list)  # machine_id -> reported buffer sizes if available
processor_metrics = defaultdict(lambda: {'cpu': deque(), 'mem': deque()})  # optional

raw_out = open(OUT_RAW, "a")
features_file = open(OUT_FEATURES, "a", newline='')
writer = csv.writer(features_file)
# header (example): timestamp, processor_id, num_machines, avg_msg_rate, median_buffer, buffer_growth, cpu,overload_label
writer.writerow(["timestamp","processor_id","num_machines","avg_msg_rate","median_buffer","buffer_growth","cpu","label"])

def now_ts():
    return int(time.time())

# raw event sink (keeps raw history for labeling offline)
def save_raw_event(ev):
    raw_out.write(json.dumps(ev) + "\n")
    raw_out.flush()
    logging.info(f"[COLLECTOR]: event recvd: {ev}")

def on_message(client, userdata, msg):
    logging.info(f"[COLLECTOR]: msg recvd: {msg}")
    topic = msg.topic
    payload = msg.payload.decode()
    ts = now_ts()
    # data messages: data/{machine_id}
    if topic.startswith("data/"):
        try:
            data = json.loads(payload)
        except:
            data = {"raw": payload}
        machine_id = topic.split("/",1)[1]
        msg_times[machine_id].append(ts)
        save_raw_event({"type":"data","ts":ts,"machine":machine_id,"payload":data})
    # processor metrics: metrics/{processor_id}
    elif topic.startswith("metrics/"):
        try:
            m = json.loads(payload)
        except:
            m = {}
        proc = topic.split("/",1)[1]
        processor_metrics[proc]['cpu'].append((ts, m.get("cpu", 0)))
        save_raw_event({"type":"metrics","ts":ts,"processor":proc,"payload":m})
    # buffer size reports: buffer/{machine_id}
    elif topic.startswith("buffer/"):
        try:
            b = int(payload)
        except:
            b = 0
        machine_id = topic.split("/",1)[1]
        buffer_sizes[machine_id].append((ts, b))
        save_raw_event({"type":"buffer","ts":ts,"machine":machine_id,"buffer":b})

client = mqtt.Client(CallbackAPIVersion.VERSION2)
client.connect(BROKER,1883,60)
client.on_message = on_message
client.subscribe("data/#")
client.subscribe("metrics/#")
client.subscribe("buffer/#")
client.loop_start()

# feature extraction loop (writes snapshot per processor approx every WINDOW)
try:
    while True:
        t0 = now_ts()
        cutoff = t0 - WINDOW
        # build per-processor aggregates by mapping machines to processors if there's mapping
        # if not, create synthetic processor "proc-1"
        proc_id = "proc-1"
        # compute per-machine rates within window
        rates = []
        buffers = []
        for mid, times in list(msg_times.items()):
            # keep only recent
            msg_times[mid] = [ts for ts in times if ts >= cutoff]
            rate = len(msg_times[mid]) / max(1, WINDOW)
            rates.append(rate)
            # buffer median
            bvals = [b for ts,b in buffer_sizes.get(mid,[]) if ts >= cutoff]
            buffers.append(bvals[-1] if bvals else 0)
        avg_rate = sum(rates)/max(1, len(rates))
        median_buffer = sorted(buffers)[len(buffers)//2] if buffers else 0
        # simple buffer growth: compare last two samples if available
        # cpu: last cpu for proc if available
        cpu = 0
        if processor_metrics[proc_id]['cpu']:
            cpu = processor_metrics[proc_id]['cpu'][-1][1]
        # label: offline compute "overload within H" by scanning raw events; here set 0 placeholder
        label = 0
        row = [t0, proc_id, max(1,len(rates)), round(avg_rate,3), median_buffer, 0, cpu, label]
        writer.writerow(row)
        features_file.flush()
        logging.info(f"[COLLECTOR]: written a row: {row}")
        time.sleep(WINDOW)
except KeyboardInterrupt:
    client.loop_stop()
    raw_out.close()
    features_file.close()

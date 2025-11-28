import time, os, json, logging, sys
import xgboost as xgb
import numpy as np
from initial_scheduler import schedule
from kubernetes import client, config
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from benchmark_collector import benchmark_cold_start_deployment, append_benchmark

logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
    format='%(asctime)s - %(levelname)s - %(message)s'
)

mqtt_client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)


############################################
# LOAD K8S CONFIG
############################################
try:
    config.load_incluster_config()
    logging.info("[AI-SCHED] Using in-cluster Kubernetes config")
except:
    config.load_kube_config()
    logging.info("[AI-SCHED] Using local .kube/config")

v1 = client.CoreV1Api()
apps = client.AppsV1Api()

############################################
# MODEL + FEATURE HANDLING
############################################

RAW_EVENTS_PATH = "/data/raw_events.jsonl"
MODEL_PATH = "/data/xgb_model.json"

FEATURES = [
    "cpu_usage","mem_usage","buffer_size","buffer_capacity",
    "avg_latency","avg_rate","temperature","vibration","load"
]


def predict_scale_decision(model, features):
    metrics = get_latest_metrics(features)

    # ordering is crucial
    row = [metrics[f] for f in features]

    dmatrix = xgb.DMatrix(
        np.array([row], dtype=float),
        feature_names=features
    )

    prob = float(model.predict(dmatrix)[0])

    return prob

def get_latest_metrics(features: list) -> dict:
    """Return dict that includes ONLY model-required features."""
    out = {f: 0.0 for f in features}  # Default to 0.0 for all features

    try:
        with open(RAW_EVENTS_PATH, "r") as f:
            # Read the first line of the .jsonl file
            line = f.readline()
            if line:  # Ensure there's a line to process
                obj = json.loads(line.strip())  # Parse the JSON object from the line
                for f in features:
                    try:
                        out[f] = float(obj.get(f, 0.0))
                    except ValueError:
                        out[f] = 0.0  # In case of conversion issues
    except Exception as e:
        logging.error(f"[AI-SCHED] No {RAW_EVENTS_PATH} found — using zeros {e}")

    return out


def load_model():
    if not os.path.exists(MODEL_PATH):
        logging.warning("[AI-SCHED] No model found -> prediction disabled.")
        return None

    model = xgb.Booster()
    model.load_model(MODEL_PATH)
    logging.info("[AI-SCHED] XGB model loaded.")

    feature_names = model.feature_names
    if feature_names is None:
        raise RuntimeError("Model has no feature names!")

    return model, feature_names


############################################
# PROCESSOR PREWARM + HYDRATION PIPELINE
############################################

def create_prewarm_processor(prob):
    """Launch a new processor pod in PREWARM mode."""
    name = "prewarm-processor"
    logging.info(f"[AI-SCHED] Creating prewarm processor: {name}")

    try:
        dep = apps.read_namespaced_deployment(name, "default")
    except:
        logging.error("[AI-SCHED] ERROR: prewarm-processor Deployment not found!")
        return None

    if prob > 0.8:
        scale_prewarm_processor(3)
    elif prob > 0.7:
        scale_prewarm_processor(2)
    else:
        scale_prewarm_processor(1)

    return name

def scale_prewarm_processor(count):
    apps.patch_namespaced_deployment_scale(
        name="prewarm-processor",
        namespace="default",
        body={"spec": {"replicas": count}}
    )
    logging.info(f"[AI-SCHED] Scaled prewarm pool to {count}")

def get_prewarm_pods():
    pods = v1.list_namespaced_pod(
        namespace="default",
        label_selector="app=prewarm-processor,mode=prewarm"
    )
    return [p.metadata.name for p in pods.items]

def hydrate_prewarm_processor(pod_name):
    """Send hydration command via MQTT"""
    logging.info(f"[AI-SCHED] Hydrating {pod_name}")

    try:
        hydration_topic = f"prewarm/{pod_name}/hydrate"
        mqtt_client.publish(hydration_topic, "1")
        logging.info(f"[AI-SCHED] Hydration published in the: {hydration_topic} topic")
    except Exception as e:
        logging.error(f"[AI-SCHED] Hydration publishing failed: {e}")

def activate_prewarm_processor(pod_name):
    """Instruct prewarmed processor to begin accepting machine assignments."""
    logging.info(f"[AI-SCHED] Activating {pod_name}")

    try:
        activation_topic = f"prewarm/{pod_name}/activate"
        mqtt_client.publish(activation_topic, "1")
        logging.info(f"[AI-SCHED] Activation published in the: {activation_topic} topic")
    except Exception as e:
        logging.error(f"[AI-SCHED] Activation publishing failed: {e}")



########################################################
# schedule: assign machines to processors.
########################################################

while True:
    ###### Begin Random scheduling #######
    schedule()
    ###### End Random scheduling #######

    ###### Begin AI scheduling #######
    model, features = load_model()
    metrics = get_latest_metrics(features)

    if model:
        prob = predict_scale_decision(model, features)
        pred = 1 if prob > 0.5 else 0
    else:
        pred = 0
        prob = 0

    logging.info(f"[AI-SCHED] Prediction={pred}, Prob={prob:.3f}")

    logging.info("[AI-SCHED] Start cold benchmark.")
    benchmark_cold_start_deployment()

    if pred == 1 or prob > 0:
        logging.info("[AI-SCHED] AI requests prewarm capacity")
        pod_name = create_prewarm_processor(prob)

        logging.info("[AI-SCHED] Wait 10 sec for prewarm-processors to rise.")
        time.sleep(10)

        # We don't need this method, we could use MQTT to store the pre-warm pod names after creation
        # That essentially brings the prewarmed pod launch to near to a few milliseconds.
        pod_names = get_prewarm_pods()

        for pod_name in pod_names:
            hydrate_prewarm_processor(pod_name)

        time.sleep(5)

        logging.info("[AI-SCHED] Start prewarm benchmark.")
        start = time.time()

        for pod_name in pod_names:
            activate_prewarm_processor(pod_name)
            finish = time.time()
            duration_ms = (finish - start) * 1000.0
            append_benchmark("prewarm", duration_ms)
            logging.info(f"[AI-SCHED] Prewarm benchmark proc: {pod_name}: time_ms={int(duration_ms)}")

    time.sleep(300)

########################################################
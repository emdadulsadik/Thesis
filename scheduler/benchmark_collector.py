import logging, sys, time, os, csv
from kubernetes import client, config

BENCHMARK_PATH = "/data/benchmark.csv"

logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
    format='%(asctime)s - %(levelname)s - %(message)s'
)

try:
    config.load_incluster_config()
    logging.info(f"[AI-SCHED: BENCHMARK] Using in-cluster Kubernetes config")
except:
    config.load_kube_config()
    logging.info(f"[AI-SCHED: BENCHMARK] Using local kubeconfig")


def append_benchmark(event_type, duration_ms):
    try:
        exists = os.path.exists(BENCHMARK_PATH)
        with open(BENCHMARK_PATH, "a", newline="") as f:
            writer = csv.writer(f)
            if not exists:
                writer.writerow(["timestamp", "event_type", "start_time_ms"])
            writer.writerow([time.time(), event_type, duration_ms])
    except Exception as e:
        logging.error(f"[AI-SCHED] Failed to write benchmark log: {e}")

def wait_for_pod_ready_by_name(pod_name, timeout=120):
    v1 = client.CoreV1Api()
    end = time.time() + timeout

    while time.time() < end:
        try:
            p = v1.read_namespaced_pod(pod_name, "default")
            if p.status.phase == "Running":
                conds = p.status.conditions or []
                for c in conds:
                    if c.type == "Ready" and c.status == "True":
                        return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def benchmark_cold_start_deployment(deploy_name="processor", label_selector="app=processor,mode!=prewarm", timeout=180):
    """
    Scale the existing deployment `deploy_name` by +1, wait for the NEW pod Ready, record time,
    then scale back to original replica count.
    """
    apps = client.AppsV1Api()
    v1 = client.CoreV1Api()

    logging.info(f"[AI-SCHED] Cold-start benchmarking started")

    # 1. get current pods and replica count
    dep = apps.read_namespaced_deployment_scale(deploy_name, "default")
    orig_replicas = dep.spec.replicas or 1

    pods_before = set(p.metadata.name for p in v1.list_namespaced_pod("default", label_selector="app=processor").items)

    # 2. scale up
    start = time.time()
    new_replicas = orig_replicas + 1
    body = {"spec": {"replicas": new_replicas}}
    apps.patch_namespaced_deployment_scale(name=deploy_name, namespace="default", body=body)

    # 3. wait for a new pod to appear and become Ready
    end_time = time.time() + timeout
    new_pod_name = None
    while time.time() < end_time:
        pods_now = v1.list_namespaced_pod("default", label_selector="app=processor").items
        names_now = set(p.metadata.name for p in pods_now)
        added = names_now - pods_before
        if added:
            # pick the first added pod
            cand = list(added)[0]
            if wait_for_pod_ready_by_name(cand, timeout=timeout):
                new_pod_name = cand
                break
        time.sleep(0.5)

    finish = time.time()
    duration_ms = (finish - start) * 1000.0

    # 4. scale back to original
    try:
        apps.patch_namespaced_deployment_scale(name=deploy_name, namespace="default", body={"spec": {"replicas": orig_replicas}})
    except Exception as e:
        logging.error(f"[AI-SCHED] failed to scale back deployment {deploy_name}: {e}")

    if new_pod_name is None:
        logging.error("[AI-SCHED] Cold-start benchmark timed out")
        return None

    append_benchmark("cold", duration_ms)
    logging.info(f"[AI-SCHED] Cold-start benchmark: pod={new_pod_name} time_ms={int(duration_ms)}")

    return duration_ms
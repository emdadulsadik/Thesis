import logging, sys, time, math
from time import sleep
from kubernetes import client, config

MAX_MACHINES_PER_PROCESSOR = 2

logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
    format='%(asctime)s - %(levelname)s - %(message)s'
)

try:
    config.load_incluster_config()
    logging.info(f"[AI-SCHED] Using in-cluster Kubernetes config")
except:
    config.load_kube_config()
    logging.info(f"[AI-SCHED] Using local kubeconfig")

#######
# Assignment Algorithm
# Given machines = [m1, m2, m3, ..., mn]
# and processors = [p1, p2, p3, ..., pk]

# Max per processor = 2
# Distribution example (n=7 machines, k=3 processors):
# ASSIGNED_MACHINES = [m1, m2] # use os.getenv(ASSIGNED_MACHINES) to get the assigned machines per processor
# ASSIGNED_MACHINES = [m3, m4] # then
# ASSIGNED_MACHINES = [m5, m6, m7]   <-- odd remainder goes here
#######

def schedule():
    running_machine_names = wait_for_pods("machine", 5)
    logging.info(f"[AI-SCHED] scheduling started with {len(running_machine_names)} machines.")
    if  running_machine_names:
        scale_processors_based_on_machines(len(running_machine_names))
        logging.info(f"[AI-SCHED] Wait 10 secs for the processors to get ready.")
        sleep(10) # Wait 30 seconds for the pods to come life
        running_processor_names = [
            name.replace('-', '_') for name in wait_for_pods("processor", 2)
        ]
        assignments_matrix = assign_machines_to_processors(running_machine_names, running_processor_names)
        update_processor_assignments(assignments_matrix)

def scale_processors_based_on_machines(num_machines: int):
    apps = client.AppsV1Api()
    required = math.floor(num_machines / MAX_MACHINES_PER_PROCESSOR)

    deploy = apps.read_namespaced_deployment_scale(
        name="processor",
        namespace="default"
    )

    current = deploy.spec.replicas

    if current == required:
        logging.info(f"[AI-SCHED] Processor count OK: {current}")
        return

    logging.info(f"[AI-SCHED] Scaling processors from {current} → {required}")

    apps.patch_namespaced_deployment_scale(
        name="processor",
        namespace="default",
        body={"spec": {"replicas": required}}
    )

def assign_machines_to_processors(machine_ids: list, processor_ids: list) -> dict:
    assignments: dict = {p: [] for p in processor_ids}
    p_idx = 0

    for m in machine_ids:
        assignments[processor_ids[p_idx]].append(m)

        if len(assignments[processor_ids[p_idx]]) >= MAX_MACHINES_PER_PROCESSOR:
            p_idx += 1
            if p_idx >= len(processor_ids):  # overflow → last one gets all remaining
                p_idx = len(processor_ids) - 1

    logging.info(f"[AI-SCHED] initial scheduling, machine assignment to processors {assignments}")

    return assignments


def update_processor_assignments(assignments: dict):
    apps = client.AppsV1Api()

    env_list = []
    for proc, machines in assignments.items():
        env_list.append({
            "name": f"ASSIGNED_MACHINES_{proc}",
            "value": ",".join(machines)
        })

    patch = {
        "spec": {
            "template": {
                "spec": {
                    "containers": [{
                        "name": "processor",
                        "env": env_list
                    }]
                }
            }
        }
    }

    apps.patch_namespaced_deployment(
        name="processor",
        namespace="default",
        body=patch
    )

    logging.info(f"[AI-SCHED] Processor assignment done: {assignments}.")


def wait_for_pods(label_selector: str, expected_count: int, timeout:int = 120) -> list:
    apps = client.CoreV1Api()
    start = time.time()

    while time.time() - start < timeout:
        pods = apps.list_namespaced_pod(
            namespace="default",
            label_selector=f"app={label_selector}"
        ).items

        running_pods = [p for p in pods if p.status.phase == "Running"]
        logging.info(f"[AI-SCHED] Found {len(running_pods)} running `{label_selector}` pods.")

        if len(running_pods) >= expected_count:
            running_pod_names = [p.metadata.name for p in running_pods]
            logging.info(f"[AI-SCHED] Ready: Found {len(running_pods)} ´{label_selector}´pods")
            return running_pod_names

        logging.info(f"[AI-SCHED] Waiting: {len(running_pods)} running pods for {label_selector}, need at least {expected_count}")
        time.sleep(3)

    raise TimeoutError(f"[AI-SCHED] Timed out waiting for {label_selector} to reach {expected_count} pods.")
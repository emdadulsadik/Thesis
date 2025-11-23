import random, time, logging, sys
from kubernetes import client, config

config.load_incluster_config()   # if inside cluster
apps_v1 = client.AppsV1Api()
core_v1 = client.CoreV1Api()

logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
    format='%(asctime)s - %(levelname)s - %(message)s'
)

MIN_MACHINES = 5
MAX_MACHINES = 15

while True:
    running_machines = core_v1.list_namespaced_pod(
        namespace="default",
        label_selector="app=machine"
    )
    running_machine_names = [p.metadata.name for p in running_machines.items]
    running_machine_count = len(running_machine_names)

    logging.info(f"[Shift] {running_machine_count} machines are running.")

    if running_machine_count < MAX_MACHINES:
        new_replicas = random.randint(MIN_MACHINES, MAX_MACHINES)
        logging.info(f"[Shift] Starting {new_replicas} new machines...")
        body = {"spec": {"replicas": new_replicas}}
        apps_v1.patch_namespaced_deployment_scale(
            name="machine",
            namespace="default",
            body=body
        )

    time.sleep(600)

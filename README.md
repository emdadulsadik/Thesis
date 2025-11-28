![simple simulation schematic.jpg](docs/simple%20simulation%20schematic.jpg)

#Simulated IoT sensor messages:

https://github.com/user-attachments/assets/4ea22da4-1ff0-4f20-8b80-0d8355aa505f


## Comprehensive Setup Guide

This guide provides the necessary steps to set up the local Kubernetes environment, configure resources, start the application, run benchmarks, and access the persistent volume data using the pvc-server component.

### Installation of Prerequisites (Mac / Windows / Linux)
We will need a container runtime (Docker/Podman), the Kubernetes CLI (kubectl), and Minikube.

#### Docker (Container Runtime)
Docker is the easiest way to manage Minikube dependencies.


| OS | Instructions                                                                                                                                                                            |
| ------------- |-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Mac/Windows | Download and install Docker Desktop from the official Docker website. Ensure it is running before proceeding.                                                                           |
| Linux  | Install Docker via our distribution's package manager (e.g., sudo apt install docker.io on Debian/Ubuntu). Ensure our user is added to the docker group: sudo usermod -aG docker $USER. |



#### Kubectl (Kubernetes Command-Line Tool)

| OS  | Instructions                                                                                                                                                                                                                                                                                             |
| ------------- |----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Mac  | `brew install kubectl`                                                                                                                                                                                                                                                                                   |
| Windows  | Use Chocolatey: `choco install kubernetes-cli`                                                                                                                                                                                                                                                           |
| Linux  | Download the binary: `curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl` <br/> <br/> and move it to our PATH: `sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl` |


#### Minikube (Local Kubernetes Cluster)

| OS  | Instructions                                                                                                                                                                                              |
| ------------- |-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Mac  | `brew install minikube`                                                                                                                                                                                     |
| Windows  | (Chocolatey) `choco install minikube`                                                                                                                                                                       |
| Linux  | Download the binary: `curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64` <br/><br/> and move it to our PATH: `sudo install minikube-linux-amd64 /usr/local/bin/minikube` |


### Minikube and Docker Configuration
Before starting, it is crucial to allocate enough resources for our Minikube VM, especially for thesis-level benchmarking, which is often resource-intensive.

#### Stopping and Deleting Previous Clusters
If we have an old Minikube cluster, it's best to start fresh:

```shell
minikube stop
minikube delete
```

#### Starting Minikube with Resources
Based on common requirements for Kubernetes benchmarking, 
we will assign 8GB of memory and 4 CPUs. 
Adjust these values based on our host machine's resources. 
We will also use the docker driver for better integration.
##### Start Minikube with 8GB memory and 4 CPUs

```shell 
minikube start --driver=docker --memory=8192mb --cpus=4
```

##### (Optional, but useful) View the status

```shell 
minikube status
```

##### Connecting Docker to Minikube's Daemon
If the project requires building custom images or ensures Minikube uses the same image cache as our local Docker environment, run this command:

##### Set our shell environment to point to the Minikube Docker daemon

```eval $(minikube docker-env)```

### Starting the Deployments
We are now ready to deploy the Kubernetes manifests from the repository.

#### Clone the Repository

```shell
git clone https://github.com/emdadulsadik/Thesis.git
cd Thesis
```

#### Apply the Manifests
Assuming all the necessary Kubernetes resources (Deployments, Services, PVCs, ConfigMaps) 
are in YAML files in our current directory, use kubectl apply.

Execute deployment, jobs and pvc manifests in the correct order: 

```shell
kubectl apply -f ai-data-pvc.yaml && 
kubectl apply -f k8s-deployment.yaml && 
kubectl apply -f collector-job.yaml && 
kubectl apply -f ai-trainer-job.yaml && 
kubectl apply -f benchmark-job.yaml 
```

To start the pvc web server: 

```shell
kubectl apply -f pvc-server.yaml && minikube service pvc-server
```

##### The main deployments are in the k8s-deployment.yaml. It contains:

1. MQTT, machine, processor and ai-scheduler deployments
2. Then there is the ai-data-pvc.yaml that defines a shared volume and is mounted against the name “training-data”. 
3. The collector-job.yaml is to collect XGB model features and save them in two files features.csv and raw_events.jsonl
4. The ai-trainer-job.yaml is to train the simple XGB model. It essentially does two things: labels the features (label_features.py) and trains the model (train_xgb.py)


In case there are issues with the benchmark or for any reason we would like to reconfig and relaunch, execute: 

kubectl delete pod,svc pvc-server && kubectl delete deployment pvc-server


#### Verify Startup
Check the status of our Pods. All Pods (including pvc-server) should eventually show a status of Running and READY 1/1.

```shell
kubectl get pods
```

### Benchmarking
#### Run the Benchmark

```shell
kubectl apply -f benchmark-job.yaml
```

#### Monitor the Job's Pod logs

```shell 
kubectl logs -f <benchmark-pod-name>
```

The benchmark process should generate output files, including the benchmark_plot.png, which will be written to the Persistent Volume Claim (PVC).

### Browsing the PVC Data

The pvc-server service is designed to access and serve the data from the PVC, 
allowing us to view our results, including benchmark_plot.png.

#### Access the Plot
After executing the 

```shell
kubectl apply -f pvc-server.yaml && minikube service pvc-server
``` 

A web browser will launch automatically and load the webpage 
on the localhost with an appropriate dynamically generated http port. 
Because we configured the pvc-server with `autoindex on;` 
(directory listing), we should see a list of files in the PVC's root directory.
Click on the link corresponding to the file: `benchmark_plot.png`.
The image should display directly in our browser.
If we encounter any issues with the plot access, 
ensure the benchmark ran successfully and the file was written to 
the mounted PVC path (`/usr/share/nginx/html`).

---

## Maintenance and Rejuvenation

This guide outlines the critical steps for updating our application images, deploying components, cleaning up finished resources, and performing data inspection within our shared Kubernetes (Minikube) environment. We will ensure our workflow is reliable and repeatable.
Image Management and Component Updates
The entire update process follows a reliable Build, Push, Redeploy cycle to ensure Kubernetes pulls the latest changes.

### Updating and Pushing Core Images
Before we can deploy new code, we must rebuild and push the updated Docker images to the registry (Docker Hub). We must first log in to Docker Hub.

#### Docker Login:
```shell 
docker login
```


#### Massive Image Rebuild: 
Rebuild all three primary images for the IoT architecture.

```shell 
docker build -t esadik/iot-processor:latest ./processors && \
docker build -t esadik/ai-scheduler:latest ./scheduler && \
docker build -t esadik/iot-simulator:latest ./sensors
```

#### Push to Docker Hub: 
Push the newly built images so the Kubernetes cluster can access them.

```shell 
docker push esadik/iot-simulator:latest && \
docker push esadik/iot-processor:latest && \
docker push esadik/ai-scheduler:latest
```

### Full Deployment Workflow (Build, Push, Redeploy for Specific Components)
For a complete update of the processor, ai-scheduler, and machine components, we use this powerful single-line command chain:

```shell 
docker build -t esadik/processor:latest ./processor && \
docker build -t esadik/ai-scheduler:latest ./scheduler && \
docker build -t esadik/machine:latest ./machine && \
docker push esadik/machine:latest && \
docker push esadik/processor:latest && \
docker push esadik/ai-scheduler:latest && \
kubectl rollout restart deployment machine && \
kubectl rollout restart deployment ai-scheduler && \
kubectl rollout restart deployment processor
```

### Job Management 
For components that run once and exit (Jobs), the workflow is slightly different (we delete the old Job and apply the new manifest).

|   Component   | Task                                       |   Command Sequence    |
|   ----------  |--------------------------------------------|------------------ |
| Collector | We ensure the latest Collector Job is run. | `docker build -t esadik/collector:latest ./collector && docker push esadik/collector:latest && kubectl delete job collector && kubectl apply -f collector-job.yaml` |
|  AI Trainer | We ensure the latest AI Trainer Job is run.                                           | `docker build -t esadik/ai-trainer:latest ./trainer && docker push esadik/ai-trainer:latest && kubectl delete job ai-trainer && kubectl apply -f ai-trainer-job.yaml`  |
| Benchmark Tool  |  We run the Performance Benchmark Job.                                          |  `docker build -t esadik/benchmark:latest ./benchmark && docker push esadik/benchmark:latest && kubectl apply -f benchmark-job.yaml` |


### Operational Maintenance and Cleanup (Rejuvenation)
We must routinely clean up our cluster to prevent resource exhaustion and ensure stability.

#### Cluster Cleanup

| Task                   | Description                                                                       | Command                                                                                                |
------------------------|-----------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| Delete ALL Completed Jobs | We find all Jobs that have finished successfully and delete them from the cluster | `kubectl delete job $(kubectl get job -o=jsonpath='{.items[?(@.status.succeeded==1)].metadata.name}')` |
| Delete ALL Failed Pods | We delete any Pods stuck in a Failed state across all namespaces.                 | `kubectl delete pods --field-selector=status.phase=Failed --all-namespaces`                            |
| Manual CronJob Trigger | If we need to run a task defined by a CronJob immediately.                        | `kubectl create job trainer-manual-run --from=cronjob/trainer`                                                                                                     |

#### Managing Continuous Deployments
List Deployments: We list the current Deployments in the default namespace.

```shell 
kubectl get deployments -n default
kubectl get deploy
```

Delete an Old Deployment: We delete a specific, outdated Deployment.

```shell 
kubectl delete deploy <old-deployment-name>
```

### Debugging and Data Inspection

#### Inspecting Data Files on the PVC
We use kubectl exec to run commands inside a Pod that has the Persistent Volume Claim (PVC) mounted (e.g., the collector Pod at /data).

|   File | Task                                                 | Command                                                                                        | 
| ------ |------------------------------------------------------|------------------------------------------------------------------------------------------------|
| Listing Files | We view the contents of the mounted /data directory. | `kubectl exec -it $(kubectl get pod -l app=collector -o name) -- ls /data`                     |
| Features Data | We view the first 5 lines of the features.csv file.  | `kubectl exec -it $(kubectl get pod -l app=collector -o name) -- head -5 /data/features.csv`   |
| Benchmark Data | We view the first 5 lines of the benchmark.csv file. | `kubectl exec -it $(kubectl get pod -l app=collector -o name) -- head -5 /data/benchmark.csv`  |

#### Debugging MQTT Messages
If we need to check the real-time message flow, 
we can shell into the MQTT Pod and use the mosquitto_sub client.
Shell into the MQTT Pod: We find the running MQTT Pod and enter its shell.

```shell
kubectl exec -it $(kubectl get pods -l app=mqtt --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}') -- sh
```

Watch Messages Live: Once inside the Pod, 
we subscribe to all topics (#) verbosely (-v).
```shell
mosquitto_sub -h localhost -t "#" -v
```

#### Extracting Data to Our Local Machine
To download the full contents of the PVC to our local machine, 
we use the kubectl cp command via a running Pod that mounts the volume (e.g., the ai-scheduler).
Set the Pod Name Dynamically:

```shell
POD_NAME=$(kubectl get pods -l app=ai-scheduler -o jsonpath='{.items[0].metadata.name}') && kubectl cp default/$POD_NAME:/data ./data
```
This will create a new ./data directory on our local machine containing the files from the PVC.

### Ground-Up Minikube Renewal
If our Minikube cluster starts consistently failing or 
acting erratically (e.g., due to networking or filesystem corruption), 
we must use the nuclear option to reset the environment completely.

```shell
minikube stop && minikube delete && minikube start
```

After this, we must re-apply all Kubernetes manifests 
(`kubectl apply -f .`) to restart the application components.
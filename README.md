<!-- TOC start (generated with https://github.com/derlin/bitdowntoc) -->

- [EnerTEF JupyterHub ML Platform Documentation](#enertef-jupyterhub-ml-platform-documentation)
   * [Overview](#overview)
   * [Architecture](#architecture)
      + [Data Flow](#data-flow)
   * [Components](#components)
   * [Helm chart files](#helm-chart-files)
      + [`base-app` - User Notebooks](#base-app-user-notebooks)
      + [`flower-app` - Flower app template](#flower-app-flower-app-template)
   * [Setup and Deployment](#setup-and-deployment)
      + [Prerequisites](#prerequisites)
      + [Custom Images (Built Locally)](#custom-images-built-locally)
      + [Deployment Steps](#deployment-steps)
   * [Usage Workflow](#usage-workflow)
      + [Basic Workflow](#basic-workflow)
   * [Advanced Features](#advanced-features)
      + [MLflow User Isolation](#mlflow-user-isolation)
      + [Integrated Extensions](#integrated-extensions)
   * [Storage Usage](#storage-usage)
   * [Troubleshooting](#troubleshooting)
      + [Service Access Issues](#service-access-issues)
      + [Notebook Startup Problems](#notebook-startup-problems)
      + [MLflow Issues](#mlflow-issues)
      + [Useful Commands](#useful-commands)
   * [Development and Customization](#development-and-customization)
      + [Adding User Scripts](#adding-user-scripts)
      + [Environment Modifications](#environment-modifications)
   * [Summary](#summary)
   * [Further Reading](#further-reading)

<!-- TOC end -->

<!-- TOC --><a name="enertef-jupyterhub-ml-platform-documentation"></a>
# EnerTEF JupyterHub ML Platform Documentation

<!-- TOC --><a name="overview"></a>
## Overview

The EnerTEF JupyterHub ML Platform is a containerized machine learning environment built on Kubernetes. It provides isolated Jupyter notebook servers for each user, integrated with experiment tracking, visualization, and storage services.

The platform includes:
- JupyterHub for multi-user notebook management.
- TensorBoard for training visualization.
- MLflow for experiment tracking and model management.
- Flower for federated learning.

A visual presentation can be found [here](docs/visualREADME.md).

<!-- TOC --><a name="architecture"></a>
## Architecture
The architecture is split: Within a single instance of this application, and accross multiple instances of the application
The following is within a single instance:

![Architecture](docs/images/architecture.png)

If flower is enabled, the flower architecture becomes relevant:

![Flower-architecture](docs/images/flower-architecture.svg)
[source](https://flower.ai)

The serverapp always ends up in the server, i.e, the superexec belonging to the superlink. This allows to provisiong both the local admin mlflow credentials on the hub instance, and the remote , user specific mlflow credentials for the client instance. The serverapp then uses that to log into both mlflow tracking servers, allowing for proper namespaced and selective model sharing:

![Exterior-architecture](docs/images/extarch.png)

Centralized and remote logging is only possible from the serverapp, because the client app can run in any arbitrary supernode ( other client ), making the superlink the center point of the setup. 
An app deployed as hub will generate certificates, these should be passed to apps deployed as nodes/clients, that they may reach the superlink.


<!-- TOC --><a name="data-flow"></a>
### Data Flow
1. Users access JupyterHub via web interface
2. Each user gets a dedicated Kubernetes pod with Jupyter notebook
3. ML tools (TensorBoard, MLflow, Flower) run as integrated extensions
4. Data persists in MinIO and PostgreSQL
5. All services communicate through Kubernetes networking

<!-- TOC --><a name="components"></a>
## Components

<!-- TOC --><a name="jupyterhub"></a>
### JupyterHub
Multi-user platform that provisions isolated Jupyter notebook environments. Each user receives a dedicated container with pre-configured tools and libraries.

<!-- TOC --><a name="tensorboard"></a>
### TensorBoard
Visualization tool for machine learning experiments. Integrated directly into notebook environment for real-time monitoring of training metrics, loss curves, and model performance.

<!-- TOC --><a name="mlflow"></a>
### MLflow
Experiment tracking and model management platform. Provides:
- Parameter and metric logging
- Model versioning and storage
- Experiment comparison
- User-based isolation (group isolation not implemented)

<!-- TOC --><a name="flower-ai"></a>
### Flower AI
Federated learning/running of ML tasks. Flower breaks down every ML process into a client and server application. These are then deployed and ran selectively in arbitrary nodes. A clientapp usually contains the actual learning process. A serverapp aggregates from multiple of the same clientapp type. This level of customization allows us to weave MLFlow around flower.

<!-- TOC --><a name="kubernetes"></a>
### Kubernetes
Container orchestration platform managing all services, networking, and resource allocation. Uses k3d for local development environments.

<!-- TOC --><a name="helm-chart-files"></a>
## Helm chart files

<!-- TOC --><a name="base-app-user-notebooks"></a>
### `base-app` - User Notebooks
Contains files and demo notebooks for the base user environment.

<!-- TOC --><a name="flower-app-flower-app-template"></a>
### `flower-app` - Flower app template
Contains a clientapp, serverapp and pyproject.toml used by the flower supernode to create an fab files it sends to the superlink

<!-- TOC --><a name="setup-and-deployment"></a>
## Setup and Deployment

<!-- TOC --><a name="prerequisites"></a>
### Prerequisites

- Kubernetes tools:
  - kubectl v1.33.2 or later
  For official installation instructions, visit:
  https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/
  ```bash
  # Install kubectl
  curl -LO "https://dl.k8s.io/release/v1.33.2/bin/linux/amd64/kubectl"
  sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
  ```
  - k3d v5.8.3 or later (with k3s v1.31.5-k3s1)
  For official installation instuctions, visit:
  https://k3d.io/stable/#releases
  ```bash
  # Install k3d
  curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash
  ```

- Helm v3.18.3 or later
  For official installation instuctions, visit:
  https://helm.sh/docs/intro/install/
  ```bash
  # Install Helm
  curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
  chmod 700 get_helm.sh
  ./get_helm.sh
  ```

Or use the cluster-starter module with the cluster manager of your choice for a setup including networking ( local or remote ), certification and git runners if needed.

<!-- TOC --><a name="custom-images-built-locally"></a>
### Custom Images (Built Locally)
All are in the images directory. Mainly to avoid installing dependencies on deployment, these images simply contain the python packages used by: The user notebook, the flower clientapp and the flower serverapp.

<!-- TOC --><a name="deployment-steps"></a>
### Deployment Steps

1. Clone repository and navigate to kubernetes directory:
```bash
git clone --recurse-submodules <repository-url>
cd AI_Experiment_Workbench
```

2. Install cluster manager of your choice, eg:
```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server" sh -s - --flannel-backend none --token 12345
```
3. Install dependencies:
```bash
cd cluster-start
chmod +x cluster-create.sh && ./cluster-create.sh
chmod +x cluster-prepate.sh && ./cluster-prepare.sh
```
4. Install chart ( change values beforehand if needed ):
```bash
helm upgrade --install mlfw -n mlfw --create-namespace ./mlflow-workbench -f mlflow-workbench/values.yaml
```

Chart gives possibility to expose everything under a hostname. For a local setup, port-forward the controller ports to localhost, and use dnsmasq for a local record pointing to the loopback address.
<!-- TOC --><a name="usage-workflow"></a>
## Usage Workflow

<!-- TOC --><a name="basic-workflow"></a>
### Basic Workflow

1. Log into JupyterHub at http://\<hostname\>:8080 using pre-configured users if no external keycloak is provided(admin-/stander-user)
2. Access pre-installed libraries and scripts in the `/notebook-scripts/` directory

<!-- TOC --><a name="advanced-features"></a>
## Advanced Features

<!-- TOC --><a name="mlflow-user-isolation"></a>
### MLflow User Isolation
This project uses the v3.0 mlflow API which provides natural workspace isolation. The notebook auth hooks make sure to create workspaces and assign the proper permissions on each login. Admin users have access to all workspaces, standard users with a given "username" have access to the workspace "ws-username"

<!-- TOC --><a name="integrated-extensions"></a>
### Integrated Extensions
- MLflow and TensorBoard accessible directly from notebooks
- Seamless integration without additional configuration


<!-- TOC --><a name="storage-usage"></a>
## Storage Usage
All data is persisted between user sessions, and only disappears on active culling of the user pod. The culling interval can be configured in the values.yaml, and so are all possible persistence volume size ( pgsql, minio, jupyter hub and mlflow )

<!-- TOC --><a name="troubleshooting"></a>
## Troubleshooting

<!-- TOC --><a name="service-access-issues"></a>
### Service Access Issues
- Verify port forwarding is active
- Check pod status: `kubectl get pods`
- Restart port forwarding if needed

<!-- TOC --><a name="notebook-startup-problems"></a>
### Notebook Startup Problems
- Check pod status: `kubectl get pods`
- View pod logs: `kubectl logs <pod-name>`
- Verify resource availability

<!-- TOC --><a name="mlflow-issues"></a>
### MLflow Issues
- Confirm PostgreSQL is running: `kubectl get pods`
- Check MLflow server logs
- Verify database connectivity

<!-- TOC --><a name="useful-commands"></a>
### Useful Commands
```bash
# Check all pods
kubectl get pods --all-namespaces

# View pod logs
kubectl logs <pod-name>

# Check resource usage
kubectl top pods
```

<!-- TOC --><a name="development-and-customization"></a>
## Development and Customization

<!-- TOC --><a name="adding-user-scripts"></a>
### Adding User Scripts
- Place scripts that should be pre-loaded in `base-app/`
- Update `requirements.txt` for new dependencies
- Scripts are automatically copied to user directories

<!-- TOC --><a name="environment-modifications"></a>
### Environment Modifications
- Modify Dockerfiles in `images` for base images
- Update Helm values in `values.yaml`
- Add services via Kubernetes manifests

<!-- TOC --><a name="summary"></a>
## Summary

This platform provides a complete ML development environment with user isolation, experiment tracking, and integrated tools. The containerized architecture ensures consistent environments while Kubernetes manages scaling and resource allocation.

The setup is suitable for both individual researchers and teams, with automatic provisioning of isolated notebook environments and shared services for collaboration.

<!-- TOC --><a name="further-reading"></a>
## Further Reading

- [JupyterHub Documentation](https://jupyterhub.readthedocs.io/)
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [TensorBoard Documentation](https://www.tensorflow.org/tensorboard)
- [MinIO Documentation](https://docs.min.io/community/minio-object-store/index.html)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
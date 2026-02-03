<!-- TOC start (generated with https://github.com/derlin/bitdowntoc) -->

- [EnerTEF JupyterHub ML Platform Documentation](#enertef-jupyterhub-ml-platform-documentation)
   * [Overview](#overview)
   * [Architecture](#architecture)
      + [Data Flow](#data-flow)
   * [Components](#components)
   * [Directory Structure](#directory-structure)
   * [Setup and Deployment](#setup-and-deployment)
      + [Prerequisites](#prerequisites)
      + [Custom Images (Built Locally)](#custom-images-built-locally)
      + [Deployment Steps](#deployment-steps)
   * [Usage Workflow](#usage-workflow)
      + [Basic Workflow](#basic-workflow)
      + [MLflow Experiment Tracking](#mlflow-experiment-tracking)
      + [TensorBoard Visualization](#tensorboard-visualization)
   * [Port Mappings](#port-mappings)
   * [Advanced Features](#advanced-features)
      + [MLflow User Isolation](#mlflow-user-isolation)
      + [Integrated Extensions](#integrated-extensions)
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
- JupyterHub for multi-user notebook management
- TensorBoard for training visualization
- MLflow for experiment tracking and model management
- MinIO for S3-compatible object storage
- PostgreSQL database with pgAdmin interface

A visual presentation can be found [here](docs/visualREADME.md).

<!-- TOC --><a name="architecture"></a>
## Architecture

![Architecture](docs/images/architecture.png)

<!-- TOC --><a name="data-flow"></a>
### Data Flow
1. Users access JupyterHub via web interface
2. Each user gets a dedicated Kubernetes pod with Jupyter notebook
3. ML tools (TensorBoard, MLflow) run as integrated extensions
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

<!-- TOC --><a name="minio"></a>
### MinIO
S3-compatible object storage for datasets, model artifacts, and logs. Accessible from notebooks for data management and persistence.

<!-- TOC --><a name="postgresql-pgadmin"></a>
### PostgreSQL & pgAdmin
- PostgreSQL: Primary database for MLflow metadata and persistent data
- pgAdmin: Web-based database administration interface

<!-- TOC --><a name="kubernetes"></a>
### Kubernetes
Container orchestration platform managing all services, networking, and resource allocation. Uses k3d for local development environments.

<!-- TOC --><a name="directory-structure"></a>
## Directory Structure

<!-- TOC --><a name="helmchart-infrastructure-configuration"></a>
### `mlfw-workbench` - Helm Chart
Contains Helm Chart template and values.

<!-- TOC --><a name="srcnotebook-scripts-user-environment-templates"></a>
### `src/notebook-scripts/` - User Environment Templates
Files automatically copied to new user home directories:
- `requirements.txt`: Python dependencies for notebooks
- `tensorboard_logger.py`: TensorBoard logging utilities
- `mlflow_group_utils.py`: MLflow user management utilities
- Example notebooks for common workflows

<!-- TOC --><a name="setup-and-deployment"></a>
## Setup and Deployment

<!-- TOC --><a name="prerequisites"></a>
### Prerequisites

- Any cluster management software: k3s, k3d, kubernetes, kind...etc

- Kubernetes tools:
  - kubectl v1.33.2 or later
  For official installation instructions, visit:
  https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/
  ```bash
  # Install kubectl
  curl -LO "https://dl.k8s.io/release/v1.33.2/bin/linux/amd64/kubectl"
  sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
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

You can use [this cluster starter](https://github.com/SystemsPurge/cluster-starter) for local setups.

<!-- TOC --><a name="custom-images-built-locally"></a>
### Custom Images (Built Locally)

- **jn-mlflow**: Built from `/jn-tb/mlflow.Dockerfile` using the start script - contains Jupyter Notebook with MLflow integration
This image ends up being referenced for the user environment in the values.yaml

<!-- TOC --><a name="deployment-steps"></a>
### Deployment Steps

1. Clone repository and navigate to kubernetes directory:
```bash
git clone <repository-url>
cd AI_Experiment_Workbench
```

2. Change top level ( anchored ) values in mlflow-workbench/values.yaml as needed.

3. Install chart:
```bash
helm upgrade --install mlfw -f mlflow-workbench/values.yaml ./mlflow-workbench --namespace mlfw --create-namespace
```
This installs the configured jupyter-hub instance, minio and postgres.

4. Access services via port forwarding:
```bash
kubectl port-forward service/<jhub-service-name> -n <deployment-namespace> <host-port>:8080
```
This will expose jupyter-hub under localhost:8080

Alternatively if you have a local dns setup, cloud-provider or loadbalancer, you can rely on
gateways/ingress by passing the corresponding domain name to the values.


<!-- TOC --><a name="usage-workflow"></a>
## Usage Workflow

<!-- TOC --><a name="basic-workflow"></a>
### Basic Workflow

1. Log into JupyterHub at http://localhost:8080
2. Create username and launch notebook server:
    - Use only alphanumeric characters (letters and numbers)
    - Username is case insensitive
3. Access pre-installed libraries and scripts in the `/notebook-scripts/` directory

<!-- TOC --><a name="mlflow-experiment-tracking"></a>
### MLflow Experiment Tracking

```python
import mlflow

# Set experiment name
mlflow.set_experiment("experiment_name")

# Log parameters, metrics, and artifacts
with mlflow.start_run():
    mlflow.log_param("learning_rate", 0.01)
    mlflow.log_metric("accuracy", 0.95)
    mlflow.log_artifact("model.pkl")
```

<!-- TOC --><a name="tensorboard-visualization"></a>
### TensorBoard Visualization

```python
from tensorboard_logger import TensorBoardLogger

logger = TensorBoardLogger()
# Use logger to track training metrics
```
<!-- TOC --><a name="port-mappings"></a>
## Port Mappings

The platform exposes several services on the following ports:

| Service               | Port  | Description                               |
|-----------------------|-------|-------------------------------------------|
| Registry              | 5001  | Docker registry for custom images         |
| JupyterHub            | 8080  | Web interface for notebook access         |
| JupyterHub Internal   | 8081  | Hub's internal service port               |
| MinIO                 | 9000  | S3-compatible object storage API          |
| MinIO Console         | 9001  | Web interface for MinIO management        |
| PostgreSQL            | 5432  | Database connection port                  |
| pgAdmin               | 5050  | Web interface for database management     |

Additionally, ports 80 and 9090 have to be opened for Kubernetes services and internal routing to work. 
This is done by the start script.

Access these services by visiting `http://localhost:<PORT>` in your web browser after using the `kubectl port-forward` command.
Or under the pre-configured hostname when enabling ingress/gateways.


**Note:** Not all services and ports are designed for web access. Some are exposed for API access, internal services, or diagnostics purposes only. These include:
- Registry port (5001) - Used for Docker image storage
- MinIO API port (9000) - For S3 API access
- PostgreSQL port (5432) - For direct database connections
- JupyterHub internal ports - For service communications

These ports are exposed to allow direct connections when needed for development, debugging, or custom integrations.

<!-- TOC --><a name="advanced-features"></a>
## Advanced Features

<!-- TOC --><a name="mlflow-user-isolation"></a>
### MLflow User Isolation
- Each user has isolated experiment tracking
- User-specific database schemas prevent data mixing
- Group-based isolation not currently implemented

<!-- TOC --><a name="integrated-extensions"></a>
### Integrated Extensions
- MLflow and TensorBoard accessible directly from notebooks
- Automatic startup with notebook environment
- Seamless integration without additional configuration

<!-- TOC --><a name="development-and-customization"></a>
## Development and Customization

<!-- TOC --><a name="adding-user-scripts"></a>
### Adding User Scripts
- Place scripts that should be pre-loaded in `src/notebook-scripts/`
- Update `requirements.txt` for new dependencies
- Scripts are automatically copied to user directories

<!-- TOC --><a name="environment-modifications"></a>
### Environment Modifications
- Modify Dockerfiles in `src/jn-tb/` for base images
- Update Helm values in `deploy/kubernetes/values/`
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
#!/bin/bash

# Set service ports
JUPYTER_PORT=8080
MINIO_PORT=9000
PGADMIN_PORT=5050
JUPYTER_HUB=8081
MINIO_CONSOLE_PORT=9001
POSTGRES_PORT=5432

# Open firewall ports if UFW is active
if sudo ufw status | grep -q active; then
  sudo ufw allow 9090
  sudo ufw allow 80
fi

# Create registry if not exists
if ! k3d registry list | grep -q enertef-registry; then
  k3d registry create enertef-registry.localhost --port 5001 > /dev/null 2>&1
  echo "Registry created."
else
  echo "Registry already exists."
fi

# Build jupyterhub image and push to local registry

echo "Building JupyterHub Docker image..." 
docker build -t k3d-enertef-registry.localhost:5001/jn-mlflow:latest -f ../jn-tb/mlflow.Dockerfile ../jn-tb/
docker push k3d-enertef-registry.localhost:5001/jn-mlflow:latest 

# Start k3d cluster (if not already running)

echo "Starting k3d cluster..."
if ! k3d cluster list | grep -q enertef-cluster; then
  k3d cluster create enertef-cluster --registry-use k3d-enertef-registry.localhost:5001 > /dev/null 2>&1
  echo "Cluster created."
else
  echo "Cluster already exists."
fi 

# Install JupyterHub with Helm (no MetalLB)
if ! helm repo list | grep -q jupyterhub; then
  echo "Adding JupyterHub Helm repository..."
  helm repo add jupyterhub https://jupyterhub.github.io/helm-chart > /dev/null 2>&1
  helm repo update > /dev/null 2>&1
else
  echo "JupyterHub Helm repository already exists."
fi
echo "Installing JupyterHub..."
helm install jupyterhub jupyterhub/jupyterhub --create-namespace --values ./values/jupyterhub.yaml > /dev/null 2>&1

# Add MinIO Helm repository if not already added
if ! helm repo list | grep -q minio-operator; then
  echo "Adding MinIO Helm repository..."  
  helm repo add minio-operator https://operator.min.io/ > /dev/null 2>&1
  helm repo update > /dev/null 2>&1
else
  echo "MinIO Helm repository already exists."
fi


# Add pgAdmin Helm repository if not already added
if ! helm repo list | grep -q runix; then
  echo "Adding pgAdmin Helm repository..."
  helm repo add runix https://helm.runix.net/ > /dev/null 2>&1
  helm repo update > /dev/null 2>&1
else
  echo "pgAdmin Helm repository already exists."
fi

# Install MinIO Operator with Helm
echo "Installing MinIO Operator..."
helm install operator minio-operator/operator --namespace minio-operator --create-namespace > /dev/null 2>&1

# Install MinIO Tenant with Helm
echo "Installing MinIO Tenant..."
helm install tenant minio-operator/tenant --namespace minio-tenant --create-namespace --values ./values/minio-tenant.yaml > /dev/null 2>&1
# Install pgAdmin with Helm
echo "Installing pgAdmin..."
helm install pgadmin runix/pgadmin4 --values ./values/pgadmin.yaml > /dev/null 2>&1


# Create ConfigMap from all .py and .ipynb files in notebook/ for default user files
echo "Creating default-files ConfigMap from notebook/*.py and notebook/*.ipynb..."
kubectl create configmap default-files \
  --from-file=$(find "$(pwd)/../notebook-scripts" -maxdepth 1 -type f \( -name '*.py' -o -name '*.ipynb' \) | paste -sd, -) \
  --dry-run=client -o yaml | kubectl apply -f -

# Create ConfigMap for pip requirements
echo "Creating pip-requirements ConfigMap from requirements.txt..."
kubectl create configmap requirements --from-file=requirements.txt="$(pwd)/../notebook-scripts/requirements.txt" --dry-run=client -o yaml | kubectl apply -f - > /dev/null 2>&1

kubectl create configmap mlflow-auth-config --from-file=basic-auth.ini="$(pwd)/../notebook-scripts/basic-auth.ini" --dry-run=client -o yaml | kubectl apply -f - > /dev/null 2>&1

# create secret
kubectl create secret generic hub-admin-token --from-literal=token='61ffe55352968aea27a26a49872eed3db4ae26cc00103f7a18bbf7307d54f964'

# Apply all manifests
kubectl apply -f db/ > /dev/null 2>&1
kubectl apply -f mlflow-secret/ > /dev/null 2>&1
# Wait for all pods to be running or completed
echo "Waiting for all pods to be ready..."
for ns in minio-operator minio-tenant default; do
  if kubectl get pods -n $ns | grep -q .; then
    kubectl wait --for=condition=Ready pod --all -n $ns --timeout=300s || true > /dev/null 2>&1
  fi
done
# Start port-forwarding and save PIDs
echo "Starting port-forwarding for services..."
> .portforward_pids

kubectl port-forward svc/proxy-public $JUPYTER_PORT:80 &
echo $! >> .portforward_pids > /dev/null 2>&1

kubectl port-forward svc/minio -n minio-tenant $MINIO_PORT:80 &
echo $! >> .portforward_pids > /dev/null 2>&1

kubectl port-forward svc/myminio-console -n minio-tenant $MINIO_CONSOLE_PORT:9090 &
echo $! >> .portforward_pids > /dev/null 2>&1

kubectl port-forward svc/db $POSTGRES_PORT:5432 &
echo $! >> .portforward_pids > /dev/null 2>&1

kubectl port-forward svc/pgadmin-pgadmin4 $PGADMIN_PORT:80 &
echo $! >> .portforward_pids > /dev/null 2>&1

kubectl port-forward svc/hub $JUPYTER_HUB:8081 &
echo $! >> .portforward_pids > /dev/null 2>&1

echo "Services should be accessible at:"
echo "  JupyterHub:        http://localhost:$JUPYTER_PORT"
echo "  MinIO Console:     http://localhost:$MINIO_CONSOLE_PORT"
echo "  pgAdmin:           http://localhost:$PGADMIN_PORT"

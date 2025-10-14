#!/bin/bash

echo "Stopping Enertef cluster and cleaning up resources..."

# Stop all port-forwarding processes
if [ -f .portforward_pids ]; then
    while read pid; do
        if kill -0 $pid 2>/dev/null; then
            echo "Killing port-forward process $pid"
            kill $pid > /dev/null 2>&1
        fi
    done < .portforward_pids
    rm .portforward_pids > /dev/null 2>&1
    echo "All port-forwarding processes stopped."
else
    echo "No port-forwarding PIDs file found."
fi


if sudo ufw status | grep -q active; then
  sudo ufw delete allow 9090
  sudo ufw delete allow 80
fi

# Optionally clean up the ConfigMap
echo "Deleting ConfigMaps..."
kubectl delete configmap default-files --ignore-not-found > /dev/null 2>&1

# Delete Helm release to clean up JupyterHub resources
echo "Uninstalling JupyterHub Helm release..."
helm uninstall jupyterhub --ignore-not-found > /dev/null 2>&1

# Delete MinIO Operator and Tenant Helm releases
echo "Uninstalling MinIO Operator and Tenant Helm releases..."
helm uninstall operator --namespace minio-operator --ignore-not-found > /dev/null 2>&1
helm uninstall tenant --namespace minio-tenant --ignore-not-found > /dev/null 2>&1

# Uninstall namespaces
echo "Deleting namespaces..."
kubectl delete namespace minio-operator --ignore-not-found > /dev/null 2>&1
kubectl delete namespace minio-tenant --ignore-not-found > /dev/null 2>&1

# Delete registry if exists
if k3d registry list | grep -q 'k3d-enertef-registry'; then
  echo "Deleting k3d registry..."
  k3d registry delete k3d-enertef-registry.localhost > /dev/null 2>&1
  echo "Registry deleted."
else
  echo "No registry to delete."
fi

# Delete custom Docker images from local Docker
echo "Removing custom Docker images..."
docker rmi k3d-enertef-registry.localhost:5001/jn-mlflow:latest > /dev/null 2>&1 || echo "Image not found or already removed."      

# Wait briefly for resources to start cleaning up
echo "Waiting for resources to begin cleanup..."
sleep 5

# Stop the k3d cluster
echo "Deleting k3d cluster..."
k3d cluster delete enertef-cluster

echo "Cleanup complete! All resources have been removed."

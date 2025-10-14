# Running JupyterHub Notebooks with GPU Support on Kubernetes (k3d Setup)

This guide summarizes how to configure JupyterHub—deployed using the [Zero to JupyterHub Helm chart](https://z2jh.jupyter.org/)—to run notebooks with access to different GPU types or on different nodes.

---

## 1. Overview of Profiles

In JupyterHub (Zero to JupyterHub Helm chart), you can define multiple runtime environments using the `profileList`. These profiles do not represent users, but rather selectable environments (e.g., CPU-only, GPU-enabled).

Example:

```yaml
singleuser:
  profileList:
    - display_name: "CPU Only"
      description: "Basic notebook without GPU"
      kubespawner_override:
        resources:
          limits:
            cpu: "1"
            memory: "2Gi"

    - display_name: "GPU Enabled"
      description: "Notebook with 1 NVIDIA GPU"
      kubespawner_override:
        resources:
          limits:
            nvidia.com/gpu: 1
        node_selector:
          gpu: "true"
```

All users see these profiles and can choose between them. If 5 users are logged in, and 3 choose GPU, then 3 pods will request a GPU each.

---

## 2. GPU Allocation in Kubernetes

In Kubernetes, GPUs are not shared by default.

| Resource | Shared Between Pods? | Released When             |
|----------|----------------------|---------------------------|
| CPU      | Yes                  | Dynamically managed       |
| Memory   | Partially            | When pod stops            |
| GPU      | No                   | When pod/server is stopped|

If a pod requests `nvidia.com/gpu: 1`, that GPU is reserved until the pod shuts down.

---

## 3. GPU Access in k3s / k3d

If you're using k3s (as in k3d), you may need to set the runtime class for GPU access:

```yaml
hub:
  config:
    KubeSpawner:
      extra_pod_config:
        runtimeClassName: nvidia
```

Ensure the NVIDIA container runtime is installed and the GPU device plugin is active:
- https://github.com/NVIDIA/k8s-device-plugin

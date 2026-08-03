<!-- TOC start (generated with https://github.com/derlin/bitdowntoc) -->

- [Cluster prep](#cluster-prep)
   * [General](#general)
   * [Networking](#networking)
      + [CNI](#cni)
      + [Loadbalancing](#loadbalancing)
      + [Ingress/Exposure](#ingressexposure)
   * [TLS Certs](#tls-certs)
   * [Storage](#storage)
      + [NFS CSI](#nfs-csi)
      + [Rook CEPH](#rook-ceph)
   * [GPU](#gpu)
      + [NVIDIA/CUDA](#nvidiacuda)
      + [ARM64 considerations](#arm64-considerations)
         - [Architecture support](#architecture-support)
         - [Device plugin](#device-plugin)
      + [GPU sharing](#gpu-sharing)
      + [Running gpu workloads](#running-gpu-workloads)

<!-- TOC end -->

<!-- TOC --><a name="cluster-prep"></a>
# Cluster prep

The following documents a specific cluster setup, in which nodes with direct hardware access or privileged capabilities are isolated from general workloads. In this case, a GPU-capable node is treated as a sensitive worker node, and access is configured so that only explicitly intended workloads can run there.

For simplicity, this assumes a two-node cluster: one control-plane node acting as the exposed management boundary, and one sensitive worker node providing hardware-specific capabilities ( in this case, GPU ).

The following also assumes a linux based OS, in this case, everything has been ran on Ubuntu 24.04 LTS.

For simplicity , microk8s is being used, although keep in mind that whatever is done through:
```bash
microk8s enable <addon>
```

Is most likely to have analogous steps on other kubernetes distributions. These usually involve manually applying manifests or installing helm charts.<br>

<!-- TOC --><a name="general"></a>
## General
The basic cluster bootstrapping only requires a few apps:
```bash
#!/usr/bin/env bash
set -euo pipefail

sudo snap install microk8s --classic

export MANIFEST_DIR="/home/ubuntu/manifests"

export METALLB_RANGE="<control-plane ip>-<control-plane ip>"

microk8s status --wait-ready

microk8s enable dns ha-cluster helm3
microk8s enable rbac metallb:${METALLB_RANGE}

microk8s enable cert-manager ingress
```

Notice how the metallb IP only contains the control-plane ( external ) IP, this will become clearer once we go over isolation.

This all happens on the machine intended to become the control-plane, subsequently we can do:

```bash
#FROM CONTROL PLANE MACHINE
microk8s add-node

#FROM WORKER MACHINE
sudo snap install microk8s --classic
microk8s join <whatever was produced by the previous "microk8s add-node" command> --worker
```
From this point onward, all operations are ran on the control-plane.
<!-- TOC --><a name="networking"></a>
## Networking

As previously stated, the goal is to isolate the gpu worker node. 

For that we need to minimize direct exposure of that node and encrypt inter-node communication where possible.

From here on out:
```bash
alias k='microk8s kubectl'
alias h='microk8s helm3'
```

<!-- TOC --><a name="cni"></a>
### CNI

Microk8s uses calico CNI by default, alternatives may include kube-ovn, cillium or flannel.

Since calico is enabled by default on microk8s, it cannot be pre-configured.

To configure encryption, we patch the felix configuration:

```bash
k patch felixconfiguration default --type='merge' -p '{"spec":{"wireguardEnabled":true}}'
```
Enabling WireGuard requires exposing port 51820 for UDP. With the default MicroK8s Calico VXLAN configuration, UDP 4789 is used for encapsulated traffic and should be considered for firewalls, routing rules, security groups (if running VMs), etc.


<!-- TOC --><a name="loadbalancing"></a>
### Loadbalancing
Metallb handles the loadbalancing, remember the line:

```bash
export METALLB_RANGE="<control-plane ip>-<control-plane ip>"
microk8s enable rbac metallb:${METALLB_RANGE}
```

This guarantees that the cluster is only ever exposed through the control-plane IP. 

If you have multiple control planes, metallb supports comma separated IP list.

```bash
export METALLB_RANGE="<control-plane-1 ip>,<control-plane-2 ip>,<control-plane-3 ip>"
microk8s enable rbac metallb:${METALLB_RANGE}
```

This effectively makes the cluster exposed by IP, and we can now expose it using ingress/gateway resources.

An alternative to metallb, also in the case of other kubernetes distributions, is ServiceLB, where restriction is easily configured through node selection on the servicelb controller pods, no explicit management of ip pools is required :

```yaml
spec:
  template:
    spec:
      nodeSelector:
        node-role.kubernetes.io/control-plane: "true"
```

<!-- TOC --><a name="ingressexposure"></a>
### Ingress/Exposure
Metallb and nginx/traefik ingress operators do not reconcile automatically. 

It is advised to use nginx ingress here ( for now ).

```bash
h repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
h install ingress-nginx ingress-nginx/ingress-nginx -n ingress-nginx --create-namespace -f nginx-values.yaml
```

Where nginx-values.yaml:

```yaml
controller:
  hostNetwork: true
  dnsPolicy: ClusterFirstWithHostNet
  nodeSelector:
    role: control-plane
```

Which would require doing:
```bash
k label <your control plane node> role=control-plane
```

You can also rely on the kubernetes labels that are automatically assigned to nodes.

hostNetwork is used here intentionally to bind ingress directly on the control-plane node. This avoids exposing ingress through a Service and keeps traffic entry points aligned with the MetalLB isolation strategy.

Keep in mind that the previous installation doesn't guarantee the proper forwarding of headers, especially during ssl redirects. 

For example, the AI workbench relies on a jupyterhub + keycloak combination for authentication, which generally involves TLS and redirects, this would, for example, require an ingress annotated as such:

```json
{
    "ingress.kubernetes.io/ssl-redirect": "true",
    "nginx.ingress.kubernetes.io/ssl-redirect": "true",
    "nginx.ingress.kubernetes.io/proxy-buffer-size": "128k",
}
```

<!-- TOC --><a name="tls-certs"></a>
## TLS Certs

The easiest setup is to only use cert-manager:

```bash
microk8s enable cert-manager
```

If the control-plane IP can be resolved from a legitimate domain, it is possible to use letsencrypt:

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt
spec:
  acme:
    email: dummy@email.com
    server: https://acme-v02.api.letsencrypt.org/directory
    privateKeySecretRef:
      name: letsencrypt-account-key
    solvers:
    - http01:
        ingress:
          ingressClassName: nginx
```

On the other hand, if this is intended to work fully internally then:

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: selfsigned-bootstrap
spec:
  selfSigned: {}
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: root-ca
  namespace: cert-manager
spec:
  isCA: true
  commonName: Root CA
  secretName: root-ca
  privateKey:
    algorithm: ECDSA
    size: 256
  duration: 87600h
  renewBefore: 720h
  issuerRef:
    name: selfsigned-bootstrap
    kind: ClusterIssuer
    group: cert-manager.io
  usages:
    - cert sign
    - crl sign
---
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: internal-ca
spec:
  ca:
    secretName: root-ca
```

This allows automated TLS certificate provisioning for HTTPS ingress ( with termination, by default ), given the proper annotation on the ingress resource:

```json
{
    "cert-manager.io/cluster-issuer": "internal-ca" ( or letsencrypt )
}
```

<!-- TOC --><a name="storage"></a>
## Storage

The goal here is to guarantee that storage backend data never lands on the worker node filesystem, the following are two different ways to achieve that with default and redundant storage. 

First, make sure the hostpath-storage addons are disabled:

```bash
:~$ microk8s status
microk8s is running
high-availability: no
  datastore master nodes: xxx.xxx.xxx.xxx:xxxx
  datastore standby nodes: none
addons:
  enabled:
    cert-manager         # (core) Cloud native certificate management
    dns                  # (core) CoreDNS
    gpu                  # (core) Alias to nvidia add-on
    ha-cluster           # (core) Configure high availability on the current node
    helm                 # (core) Helm - the package manager for Kubernetes
    helm3                # (core) Helm 3 - the package manager for Kubernetes
    metallb              # (core) Loadbalancer for your Kubernetes cluster
    nvidia               # (core) NVIDIA hardware (GPU and network) support
    rbac                 # (core) Role-Based Access Control for authorisation
  disabled:
    cis-hardening        # (core) Apply CIS K8s hardening
    community            # (core) The community addons repository
    dashboard            # (core) The Kubernetes dashboard
    host-access          # (core) Allow Pods connecting to Host services smoothly
    hostpath-storage     # (core) Storage class; allocates storage from host directory
    ingress              # (core) Ingress controller for external access
    kube-ovn             # (core) An advanced network fabric for Kubernetes
    mayastor             # (core) OpenEBS MayaStor
    metrics-server       # (core) K8s Metrics Server for API access to service metrics
    minio                # (core) MinIO object storage (DEPRECATED). This addon is deprecated and will be completely removed in the upcoming versions
    observability        # (core) A lightweight observability stack for logs, traces and metrics
    prometheus           # (core) Prometheus operator for monitoring and logging
    registry             # (core) Private image registry exposed on localhost:32000
    rook-ceph            # (core) Distributed Ceph storage using Rook
    storage              # (core) Alias to hostpath-storage add-on, deprecated
```
<!-- TOC --><a name="nfs-csi"></a>
### NFS CSI

We first need to install an NFS server on the nodes where we want PVC data to physically reside:

```bash
sudo apt-get install nfs-kernel-server 

#make your share
mkdir -p /srv/nfs/microk8s
```

Pretty straightforward to configure, just this in your /etc/exports
```
/srv/nfs/microk8s 
  <control plane ip>(rw,sync,no_subtree_check,no_root_squash,insecure)  
  <worker ip>(rw,sync,no_subtree_check,no_root_squash,insecure)
```
Apply the configuration, up to a restart of nfs-server:

```bash
sudo exportfs -ra
```

Now the cluster needs to become aware, we use the nfs csi driver

```bash
h repo add csi-driver-nfs https://raw.githubusercontent.com/kubernetes-csi/csi-driver-nfs/master/charts
h repo update
h upgrade --install csi-driver-nfs -n nfs-csi --create-namespace \
    csi-driver-nfs/csi-driver-nfs --version 4.13.4\
    -f nfs-csi-values.yaml
```

The nfs-csi values, are primarly used in the case where microk8s is used:
```yaml
node:
  dnsPolicy: "ClusterFirstWithHostNet"

controller:
  dnsPolicy: "ClusterFirstWithHostNet"

kubeletDir: "/var/snap/microk8s/common/var/lib/kubelet"
```

Finally we create a single default storageclass, so that it is guaranteed to always be the one used:

```bash
k apply -f storageclass.yaml
```

Where the storageclass.yaml:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: nfs-csi
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: nfs.csi.k8s.io
parameters:
  server: <your control plane ip>
  share: <your nfs share folder (previously /srv/nfs/microk8s)>
reclaimPolicy: Delete
volumeBindingMode: Immediate
allowVolumeExpansion: true
mountOptions:
  - nfsvers=4.1
```


<!-- TOC --><a name="rook-ceph"></a>
### Rook CEPH
If the workload is high/fragmented/distributed across many users, then pods/pvcs will be created and destroyed on a regular basis, redundant storage might be more useful here. 

It exists on microk8s as an addon:

```bash
microk8s enable rook-ceph
```
Isolation is much more straightforward here, as it is entirely dependent on the rook-ceph configuration. We can just overwrite the CephCluster resource created by the operator:

```yaml
apiVersion: ceph.rook.io/v1
kind: CephCluster
metadata:
  name: rook-ceph
  namespace: rook-ceph
spec:
  storage:
    useAllNodes: false
    useAllDevices: false
    nodes:
      - name: <control plane node name>
        devices:
          - name: <storage disk device name>
      - name: <another control plane node name>
        devices:
          - name: <storage disk device name>
```

Unlike nfs-csi, rook-ceph relies on disks, and requires an empty storage device. 

You could use the disks available to you directly:

```bash
lsblk
```

Or , for example, create an LVM logical volume ( although this is not recommended for rook-ceph in general ):

```bash
pvcreate /dev/sdb
vgcreate ceph-vg /dev/sdb
lvcreate -L 500G -n ceph-lv ceph-vg
```
Keep in mind that Rook Ceph also depends on host-level kernel support. 

For RBD-backed volumes, the required kernel modules (such as rbd) must be available on the nodes consuming Ceph volumes.

<!-- TOC --><a name="gpu"></a>
## GPU
Keep in mind that the NVIDIA kernel driver must be available on the host before enabling Kubernetes GPU support.
The GPU node is in our case the sensitive worker node, as it is intended to provide direct
access to hardware. That access has to be restricted, for that, we taint the node to prevent
general workloads from being scheduled:

```bash
#Feel free to pick any taint
k taint nodes <gpu-worker-node> dedicated=gpu-user-env:NoSchedule

#Also useful to explicitly label it
k label nodes <gpu-worker-node> role=gpu-worker
```

<!-- TOC --><a name="nvidiacuda"></a>
### NVIDIA/CUDA

We need the microk8s nvidia addon:

```bash
microk8s enable gpu
```

Due to a discrepancy in the names of the runtime classes produced by the gpu operator,
and the runtime classes defined in the containerd configuration, on microk8s, we need to recreate the default
runtime class:

```yaml
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: nvidia-container-runtime
handler: nvidia-container-runtime
```

```bash
k delete runtimeclass nvidia
k apply -f runtimeclass.yaml
```

<!-- TOC --><a name="arm64-considerations"></a>
### ARM64 considerations

<!-- TOC --><a name="architecture-support"></a>
#### Architecture support

The microk8s gpu addon requires some configuration BEFORE enabling, as it only lists amd 
under its supported architectures by default, 
for that we modify /var/snap/microk8s/common/addons/core/addons.yaml and add `arm64` to the supported_architectures of the gpu and nvidia addons.

<!-- TOC --><a name="device-plugin"></a>
#### Device plugin
Normally the gpu operator enabled by the microk8s gpu addon, will run its own k8s device plugin by default. 
However in the case of arm64, the device plugin needs to be installed manually, you can modify [this](https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/refs/tags/v0.18.0/deployments/static/nvidia-device-plugin.yml) to add the following to the pod spec:

```yaml
nodeSelector:
  role: gpu-worker # or whatever label you are using
tolerations: # or whatever taints you defined
  - key: dedicated
    operator: Equal
    value: gpu-user-env
    effect: NoSchedule
```

Make sure it is in the same namespace as the gpu operator.

<!-- TOC --><a name="gpu-sharing"></a>
### GPU sharing

Ideally your system supports MIG/MPS, which can be enabled by creating a configuration file:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: nvidia-device-plugin-config
  namespace: <gpu operator namespace>
data:
  <profile name>: |-
    version: v1
    ...
```
You can find more info on that type of sharing [here](https://github.com/nvidia/k8s-device-plugin)

We then need to label the nodes, on which this config should be viable, as such:

```bash
k label node <worker node> nvidia.com/device-plugin.config=<profile name>
```

And patch the clusterpolicy accordingly:

```bash
kubectl patch clusterpolicies.nvidia.com/cluster-policy \
    -n <gpu operator namespace> --type merge \
    -p '{"spec": {"devicePlugin": {"config": {"name": "nvidia-device-plugin-config"}}}}'
```

More info [here](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/gpu-sharing.html).

If MIG is not supported, one way to achieve this is with time slicing:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: time-slicing-config-all
  namespace: <gpu operator namespace>
data:
  time-slicing-profile: |-
    version: v1
    flags:
      migStrategy: none
    sharing:
      timeSlicing:
        failRequestsGreaterThanOne: true
        resources:
        - name: nvidia.com/gpu
          replicas: 4
```

In the case of an arm64 architecture, we need to change our manually deployed device plugin to use that config:

```yaml
containers:
  - name: nvidia-device-plugin-ctr
    args:
      - --config-file=/config/time-slicing-profile.yaml
  volumeMounts:
    - name: plugin-config
      mountPath: /config
      readOnly: true
volumes:
  - name: plugin-config
    configMap:
      name: time-slicing-config-all
```

<!-- TOC --><a name="running-gpu-workloads"></a>
### Running gpu workloads

GPU workloads must explicitly request GPU resources, and use the runtimeclass we created. Any pod intended for GPU usage should declare under its spec:

```yaml
spec:
  runtimeClassName: nvidia-container-runtime
  containers:
  - name: workload
    resources:
      limits:
        nvidia.com/gpu: 1
```

Keep in mind that you would also have to explicitly add tolerations to the pod, otherwise it wouldnt land on the worker node:
```yaml
spec:
  tolerations: # or whatever taints you defined
    - key: dedicated
      operator: Equal
      value: gpu-user-env
      effect: NoSchedule
```
Without the resource requests, kubernetes will NOT mount the gpu devices under /dev.
Without the runtimeClassName, the container will not have the nvidia binaries ( e.g nvidia-smi ).

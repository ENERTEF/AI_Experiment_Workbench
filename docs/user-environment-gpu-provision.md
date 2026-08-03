# GPU support on jupyterhub notebooks

**DISCLAIMER**: Most of the concepts mentioned here are already explained in the cluster-setup documentation.

The AI workbench helm chart exposes the Zero2JupyterHub values directly in the values files, under the jhub_central block.

Keep in mind that the following is under jhub_central.singleuser.

Add the following if you labeled your gpu node:

```yaml
nodeSelector:
    role: gpu-worker
```

In case of a taint:

```yaml
extraTolerations:
    - key: "dedicated"
      operator: "Equal"
      value: "gpu-user-env"
      effect: "NoSchedule"
```

Resources requests to have the devices mounted:

```yaml
extraResource:
    limits:
    nvidia.com/gpu: 1
    guarantees:
    nvidia.com/gpu: 1
```

And finally the intended runtime class, to get the gpu/cuda binaries:

```yaml
extraPodConfig:
    runtimeClassName: nvidia-container-runtime
```

This , ( and a custom choice of image ), will not interfere with the chart's configuration hook
that sets up the user environment. If you want to use your own image, just do:

```yaml
image:
    name: <your image>
    tag: <your tag>
```
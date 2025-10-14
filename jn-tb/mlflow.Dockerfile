# Use the official Jupyter TensorFlow notebook image as the base
FROM jupyter/tensorflow-notebook:latest

# Install jupyter-server-proxy and TensorBoard (if not already included)
RUN pip install --no-cache-dir --upgrade \
    jupyter-server-proxy \
    tensorboard \
    jupyter-tensorboard-proxy
COPY mlflow-extension/jupyter-mlflow-proxy /usr/local/src/jupyter-mlflow-proxy
COPY ./start-notebook.sh /usr/local/bin/start-notebook.sh
USER root
RUN pip install /usr/local/src/jupyter-mlflow-proxy
RUN chmod +x /usr/local/bin/start-notebook.sh
USER jovyan
# Enable the server proxy extension
RUN jupyter server extension enable --sys-prefix jupyter_server_proxy

# docker build -t k3d-enertef-registry.localhost:5001/jn-mlflow:latest -f mlflow.Dockerfile .
# docker push k3d-enertef-registry.localhost:5001/jn-mlflow:latest
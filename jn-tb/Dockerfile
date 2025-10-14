# Use the official Jupyter TensorFlow notebook image as the base
FROM jupyter/tensorflow-notebook:latest

# Install jupyter-server-proxy and TensorBoard (if not already included)
RUN pip install --no-cache-dir --upgrade \
    jupyter-server-proxy \
    tensorboard \
    jupyter-tensorboard-proxy

COPY start-notebook.sh /usr/local/bin/start-notebook.sh
USER root
RUN chmod +x /usr/local/bin/start-notebook.sh
USER jovyan
# Enable the server proxy extension
RUN jupyter server extension enable --sys-prefix jupyter_server_proxy

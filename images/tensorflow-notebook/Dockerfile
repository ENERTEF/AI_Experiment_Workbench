FROM jupyter/tensorflow-notebook
USER root
RUN apt-get update && apt-get install -y socat
ADD requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN jupyter server extension enable --user jupyter_server_proxy
USER jovyan
CMD jupyterhub-singleuser
FROM jupyter/tensorflow-notebook
USER root
RUN apt-get update && apt-get install -y socat

ADD requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN jupyter server extension enable --user jupyter_server_proxy

#we basically need to rewrap flwr
RUN mv /opt/conda/bin/flwr /opt/conda/bin/flwr.real
COPY flwr-wrapper.sh /opt/conda/bin/flwr

RUN chmod +x /opt/conda/bin/flwr && \
    chown root:root /opt/conda/bin/flwr

USER jovyan
CMD jupyterhub-singleuser
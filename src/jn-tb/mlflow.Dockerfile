FROM jupyter/tensorflow-notebook:latest

RUN pip install --no-cache-dir --upgrade \
    jupyterhub \
    jupyter-server-proxy \
    tensorboard \
    jupyter-tensorboard-proxy


COPY mlflow-extension/jupyter-mlflow-proxy /usr/local/src/jupyter-mlflow-proxy
COPY ./start-notebook.sh /usr/local/bin/start-notebook.sh

USER root

# Install pyenv dependencies
RUN apt-get update && apt-get install -y \
    build-essential curl git libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev wget llvm \
    libncurses5-dev libncursesw5-dev xz-utils tk-dev \
    libffi-dev liblzma-dev

# Install pyenv
RUN git clone https://github.com/pyenv/pyenv.git /home/jovyan/.pyenv

# Set up pyenv environment variables
ENV PYENV_ROOT="/home/jovyan/.pyenv"
ENV PATH="$PYENV_ROOT/bin:$PATH"

# Initialize pyenv for all shells
RUN echo 'export PYENV_ROOT="/home/jovyan/.pyenv"' >> /etc/profile.d/pyenv.sh \
    && echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> /etc/profile.d/pyenv.sh \
    && echo 'eval "$(pyenv init --path)"' >> /etc/profile.d/pyenv.sh

ENV POSTGRES_HOST=postgres
ENV POSTGRES_DATABASE=mlflow
ENV POSTGRES_USER=mlflow
ENV POSTGRES_PASSWORD=mlflow
ENV POSTGRES_PORT=5432

ENV MINIO_HOST=minio
ENV MINIO_BUCKET=mlflow
ENV MINIO_USER=mlflow
ENV MINIO_PASSWORD=mlflow
ENV MINIO_PORT=9000

RUN pip install /usr/local/src/jupyter-mlflow-proxy
RUN chmod +x /usr/local/bin/start-notebook.sh
USER jovyan
RUN jupyter server extension enable --sys-prefix jupyter_server_proxy

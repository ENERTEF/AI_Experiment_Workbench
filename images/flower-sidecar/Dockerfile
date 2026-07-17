FROM python:3.11-slim
RUN apt update
RUN apt-get install -y gettext
WORKDIR /app
COPY . .
RUN chmod +x flwr-proxy.py
RUN pip install -r requirements.txt && \
    rm requirements.txt
RUN mkdir .pipes
RUN mkdir flower/user
RUN mkdir -p /root/.flwr
ENV IN_PIPE=/app/.pipes/in.pipe
ENV OUT_PIPE=/app/.pipes/out.pipe
ENV ROOT_CERT_PATH=/etc/ssl/certs/ca-certificates.crt

CMD ["sh","-c","envsubst < tpls/pyproject.toml.tpl > pyproject.toml && envsubst < tpls/config.toml.tpl > /root/.flwr/config.toml && python3 flwr-proxy.py"]
FROM flwr/superexec:latest

WORKDIR /app

COPY pyproject.toml .
RUN python -m pip install -U --no-cache-dir .
ENTRYPOINT ["flower-superexec"]+
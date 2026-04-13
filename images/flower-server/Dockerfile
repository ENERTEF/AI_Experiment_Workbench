FROM flwr/superexec:latest

WORKDIR /app

COPY pyproject.toml .
COPY server.py .
RUN python -m pip install -U --no-cache-dir .
ENTRYPOINT ["flower-superexec"]
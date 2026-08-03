FROM flwr/superexec:latest

WORKDIR /app

#according to docs, this is enough
COPY pyproject.toml .
RUN python -m pip install -U --no-cache-dir .
ENTRYPOINT ["flower-superexec"]
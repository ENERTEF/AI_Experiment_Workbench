FROM ghcr.io/mlflow/mlflow:latest
RUN pip install mlflow[auth,db,databricks]
ENV CORS_ALLOWED_ORIGINS="http://localhost"
ENV ARTIFACT_DESTINATION="s3://mlflow"
ENV POSTGRES_URI="localhost:5432"
CMD mlflow server \
        --app-name basic-auth \
        --host 0.0.0.0 \
        --port 5000 \
        --cors-allowed-origins $CORS_ALLOWED_ORIGINS \
        --serve-artifacts \
        --enable-workspaces \
        --backend-store-uri $POSTGRES_URI \
        --artifacts-destination $ARTIFACT_DESTINATION
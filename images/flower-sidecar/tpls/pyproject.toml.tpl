[project]
name = "flower-test"
version = "1.0.0"
description = "Manual testing of Supernode/Superlink"
dependencies = [
    "mlflow"
]

[tool.flwr.app]
publisher = "acs"

[tool.flwr.app.config]
mlflow_tracking_uri="${MLFLOW_EXTERNAL_TRACKING_URI}"
mlflow_tracking_username="${MLFLOW_TRACKING_USERNAME}"
mlflow_tracking_password="${MLFLOW_TRACKING_PASSWORD}"
mlflow_workspace="${MLFLOW_WORKSPACE}"

[tool.flwr.app.components]
serverapp = "server:app"
clientapp = "client:app"

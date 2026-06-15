#!/bin/bash

if [ "$1" != "run" ]; then
    exec /opt/conda/bin/flwr.real "$@"
fi

USER_URI=$MLFLOW_EXTERNAL_TRACKING_URI
USERNAME=$MLFLOW_TRACKING_USERNAME
PASSWORD=$MLFLOW_TRACKING_PASSWORD
WORKSPACE=$MLFLOW_WORKSPACE

CONFIG_STRING="mlflow_tracking_uri='${USER_URI}' mlflow_tracking_username='${USERNAME}' mlflow_tracking_password='${PASSWORD}' mlflow_workspace='${WORKSPACE}'"

exec /opt/conda/bin/flwr.real \
  "$@" \
  --run-config="${CONFIG_STRING}"
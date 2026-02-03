#!/bin/bash

export TF_CPP_MIN_LOG_LEVEL=3 


if [ -f /requirements.txt ]; then
    echo "Current user: $(whoami)"
    echo "Installing Python packages from /requirements.txt..."
    pip install --no-cache-dir --user -r /requirements.txt
    # Get the username from environment
    URL="$JUPYTERHUB_SERVICE_URL"
    TOKEN="$JUPYTERHUB_API_TOKEN"
    echo "Current url: $URL"    
fi
jupyterhub-singleuser "$@" &

until curl -s -o /dev/null "http://127.0.0.1:8888/api"; do
    sleep 2
done

# Trigger MLflow extension
python3 -c "
import os, requests
username = os.environ.get('JUPYTERHUB_USER')
token = os.environ.get('JUPYTERHUB_API_TOKEN')
url = f'http://127.0.0.1:8888/user/{username}/mlflow/'
requests.get(url, headers={'Authorization': f'token {token}'})
"
wait
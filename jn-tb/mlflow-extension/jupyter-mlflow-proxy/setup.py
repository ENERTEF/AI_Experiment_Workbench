# filepath: /home/ubuntu/enertef_hazem/jn-tb/mlflow-extension/jupyter-mlflow-proxy/setup.py
from setuptools import setup, find_packages

setup(
    name="jupyter-mlflow-proxy",
    version="0.1.0",
    description="Jupyter server proxy for MLflow UI (per-user instance)",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "jupyter-server-proxy",
        "mlflow"
    ],
    include_package_data=True,
    entry_points={
        "jupyter_serverproxy_servers": [
            "mlflow = jupyter_mlflow_proxy:setup_mlflow"
        ]
    },
    package_data={
        "jupyter_mlflow_proxy": ["icons/mlflow.svg"]
    },
)
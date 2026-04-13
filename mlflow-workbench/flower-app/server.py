from typing import List, Tuple
import numpy as np
import mlflow
from flwr.app import ArrayRecord,MetricRecord
from flwr.serverapp import ServerApp
from flwr.serverapp.strategy import FedAvg
from datetime import datetime

app = ServerApp()

def weighted_average(results, weighted_by_key):
    metrics_list = [r["metrics"] for r in results]
    losses = [m["loss"] * m[weighted_by_key] for m in metrics_list]
    total_examples = sum([m[weighted_by_key] for m in metrics_list])
    aggregated_metrics = {"loss": sum(losses) / total_examples}
    return MetricRecord(aggregated_metrics)


@app.main()
def main(grid,context):
    remote_client = None
    hub_client = None
    hub_uri = os.environ.get("HUB_SYSTEM_MLFLOW_URI")
    hub_user = os.environ.get("HUB_SYSTEM_MLFLOW_USER")
    hub_pass = os.environ.get("HUB_SYSTEM_MLFLOW_PASS")
    #hub_client = mlflow.MlflowClient(tracking_uri=hub_uri)

    is_remote = context.run_config.get("run-remote", "false").lower() == "true"
    if is_remote:
        remote_uri = context.run_config.get("user-mlflow-uri")
        remote_user = context.run_config.get("user-mlflow-username")
        remote_pass = context.run_config.get("user-mlflow-password")
        #remote_client = mlflow.MlflowClient(tracking_uri=remote_uri)
        
    with mlflow.start_run(run_name=datetime.now().strftime("%Y%m%d_%H%M%S")):
        strategy = FedAvg(
            evaluate_metrics_aggr_fn=weighted_average,
            weighted_by_key="num-examples",
            min_available_nodes=1,
            min_train_nodes=1,
            min_evaluate_nodes=1
        )
        result = strategy.start(
            grid=grid,
            initial_arrays=arrays,
            num_rounds=3,
        )
        
from typing import List, Tuple
import numpy as np
import mlflow
from flwr.app import ArrayRecord,MetricRecord
from flwr.serverapp import ServerApp
from flwr.serverapp.strategy import FedAvg
from datetime import datetime
from flwr.common import ArrayRecord

app = ServerApp()

def weighted_average(results, weighted_by_key):
    metrics_list = [r["metrics"] for r in results]
    losses = [m["loss"] * m[weighted_by_key] for m in metrics_list]
    total_examples = sum([m[weighted_by_key] for m in metrics_list])
    aggregated_metrics = {"loss": sum(losses) / total_examples}
    return MetricRecord(aggregated_metrics)


@app.main()
def main(grid,context):
    ndarrays = [
        np.random.randn(10, 5).astype(np.float32),
        np.zeros(5).astype(np.float32)
    ]

    arrays = ArrayRecord(ndarrays)
    with mlflow.start_run():
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
        
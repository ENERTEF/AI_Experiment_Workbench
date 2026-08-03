from typing import List, Tuple
import numpy as np
import mlflow
from flwr.app import ArrayRecord,MetricRecord,MessageType,ConfigRecord,Message,RecordDict
from flwr.serverapp import ServerApp
from flwr.serverapp.strategy import FedAvg
from logging import INFO
import time
import os
import multiprocessing
from flwr.common.logger import log

app = ServerApp()
os.environ["MLFLOW_TRACKING_INSECURE_TLS"] = "true"

class GridProxy:
    def __init__(self, original_grid, allowed_node_ids: List[int]):
        self._grid = original_grid
        self.allowed_node_ids = allowed_node_ids

    def get_node_ids(self) -> List[int]:
        return self.allowed_node_ids

    def send_and_receive(self, messages: List[Message], timeout: float = 3600) -> List[Message]:
        filtered_messages = [
            msg for msg in messages 
            if msg.metadata.dst_node_id in self.allowed_node_ids
        ]
        
        if not filtered_messages:
            return []
            
        return self._grid.send_and_receive(filtered_messages, timeout=timeout)

def weighted_average(results,failures=None):
    weighted_by_key = "num-examples"
    metrics_list = [r["metrics"] for r in results]
    losses = [m["loss"] * m[weighted_by_key] for m in metrics_list]
    total_examples = sum([m[weighted_by_key] for m in metrics_list])
    aggregated_metrics = {"loss": sum(losses) / total_examples}
    return MetricRecord(aggregated_metrics)


@app.main()
def main(grid,context):
    required_tags = context.run_config["dataset_tags"]
    ndarrays = [
        np.random.randn(11).astype(np.float32),
        np.zeros(1).astype(np.float32)
    ]
    node_ids = grid.get_node_ids()
    messages = []
    for _id in node_ids:
        messages.append(Message(
            content=RecordDict({"query_request":ConfigRecord({"dataset_tags":required_tags})}),
            message_type=MessageType.QUERY,
            dst_node_id=_id,
        ))
    
    replies = grid.send_and_receive(messages)
    id_tag_map = {}
    allowed_ids = []
    for reply in replies:
        _id = reply.metadata.src_node_id
        has_tag = reply.content["query_response"]["has_tag"]
        if len(has_tag) != 0:
            allowed_ids.append(_id)
            id_tag_map[str(_id)] = has_tag
        log(INFO, "Node %d replied: %s", _id, reply.content["query_response"]["has_tag"])
    
    smaller_grid = GridProxy(grid, allowed_node_ids=allowed_ids)
    arrays = ArrayRecord(ndarrays)
    run_config = ConfigRecord(id_tag_map)
    strategy = FedAvg(
        evaluate_metrics_aggr_fn=weighted_average,
        weighted_by_key="num-examples",
        min_available_nodes=1,
        min_train_nodes=1,
        min_evaluate_nodes=1
    )
    result = strategy.start(
        grid=smaller_grid,
        train_config=run_config,
        evaluate_config=run_config,
        initial_arrays=arrays,
        num_rounds=1,
    )
    user_mlflow_config = {
        "tracking_uri": context.run_config["mlflow_tracking_uri"],
        "username": context.run_config["mlflow_tracking_username"],
        "password": context.run_config["mlflow_tracking_password"],
        "workspace": context.run_config["mlflow_workspace"]
    }
    _log(None,result,context)
    _log(user_mlflow_config,result,context)

def _log(mlflow_config:dict ,result,context):
    """
    Isolated worker function meant to run inside a separate process.
    mlflow_config expects: {
        "tracking_uri": "...",
        "username": "...",
        "password": "...", 
        "workspace": "...",
    }
    """
    ts = int(time.time())
    run_name=""
    target_experiment=""
    if mlflow_config is not None:
        os.environ["MLFLOW_TRACKING_URI"] = mlflow_config["tracking_uri"]
        os.environ["MLFLOW_TRACKING_USERNAME"] = mlflow_config["username"]
        os.environ["MLFLOW_TRACKING_PASSWORD"] = mlflow_config["password"]
        os.environ["MLFLOW_WORKSPACE"] = mlflow_config["workspace"]
        run_name=f'{mlflow_config["tracking_uri"]}-{mlflow_config["username"]}-{ts}'
        target_experiment="fed-exp"
    else:
        run_name=f'central-fed-ts'
        target_experiment = "Default"
    ndarrays = result.arrays.to_numpy_ndarrays()
    local_weights_filename = f"global_weights_{ts}.npz"
    local_weights_path = os.path.join("/tmp", local_weights_filename)
    np.savez_compressed(local_weights_path, *ndarrays)
    
    mlflow.set_experiment(target_experiment)
    with mlflow.start_run(run_name=run_name):
        if result:
            for server_round, metric_record in result.train_metrics_clientapp.items():
                for metric_key, metric_value in metric_record.items():
                    mlflow.log_metric(f"train_{metric_key}", float(metric_value), step=server_round)
                    
            for server_round, metric_record in result.evaluate_metrics_clientapp.items():
                for metric_key, metric_value in metric_record.items():
                    mlflow.log_metric(f"eval_one_{metric_key}", float(metric_value), step=server_round)

            for server_round, metric_record in result.evaluate_metrics_serverapp.items():
                for metric_key, metric_value in metric_record.items():
                    mlflow.log_metric(f"eval_all_{metric_key}", float(metric_value), step=server_round)
        if context.run_config:
            stringified_params = {
                str(k): (str(v) if isinstance(v, (dict, list, tuple)) else v)
                for k, v in context.run_config.items()
                if str(k) not in {'mlflow_tracking_password'}
            }
            mlflow.log_params(stringified_params)
        mlflow.log_artifact(local_weights_path, artifact_path="model_parameters")
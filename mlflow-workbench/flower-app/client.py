
import numpy as np
from flwr.app import ArrayRecord, Context, Message, MetricRecord, RecordDict
from flwr.clientapp import ClientApp

app = ClientApp()

@app.train()
def train(msg: Message, context: Context):
    ndarrays = msg.content["arrays"].to_numpy_ndarrays()

    updated_model = [m + np.random.normal(0, 0.01, size=m.shape) for m in ndarrays]

    model_record = ArrayRecord(updated_model)
    metrics = {
        "loss": 0.5,
        "accuracy": 0.9,
        "num-examples": 100,
    }
    
    content = RecordDict({
        "arrays": model_record, 
        "metrics": MetricRecord(metrics)
    })
    
    return Message(content=content, reply_to=msg)

@app.evaluate()
def evaluate(msg: Message, context: Context):
    # Dummy evaluation
    metrics = {
        "loss": 0.5,
        "accuracy": 0.9,
        "num-examples": 50,
    }
    content = RecordDict({"metrics": MetricRecord(metrics)})
    return Message(content=content, reply_to=msg)



import numpy as np
import mlflow
from sklearn.metrics import mean_squared_error
from sklearn.linear_model import SGDRegressor
from flwr.app import ArrayRecord, Context, Message, MetricRecord, RecordDict,ConfigRecord
from flwr.clientapp import ClientApp
from logging import INFO
from flwr.common.logger import log
import os
app = ClientApp()

#It is strictly an assumption here, that the file is CSV
#We may need to implement more custom handlers 
#or a wrapper for a format normalization strategy
#_for = one of training or evaluation
def retrieve_dataset(dataset_tag,_for):
    fed_exp_id = os.environ["FEDERATED_EXPERIMENT_ID"]
    client = mlflow.tracking.MlflowClient()
    runs = client.search_runs(
        experiment_ids=[fed_exp_id],
        filter_string=f"attributes.run_name = '{dataset_tag}'",
        max_results=2
    )
    if len(runs) == 0:
        raise 'No associated run to dataset tag' 
    runs = [x for x in runs if x.inputs.dataset_inputs[0].tags[0].value == _for]
    if len(runs) == 0:
        raise f'No {dataset_tag} dataset with context {_for}'
    run = runs[0]
    if len(run.inputs.dataset_inputs) == 0:
        raise 'Input run corrupt: No dataset entries'
    dataset_info = run.inputs.dataset_inputs[0].dataset
    dataset_source = mlflow.data.get_source(dataset_info)
    file_path = dataset_source.load()
    #This may need to be passed as a configuration
    #Or probably assigned to the dataset as an attribute entirely
    target_column = "quality"
    import pandas as pd
    df = pd.read_csv(file_path,delimiter=";")
    #Features
    X = df.drop(columns=[target_column]).to_numpy(dtype=np.float32)
    #Results
    Y = df[target_column].to_numpy(dtype=np.float32)
    return X,Y

@app.query()
def query(msg: Message, context: Context) -> Message:
    own_tags = context.node_config["dataset_tags"].split(",")
    required_tags_dict = msg.content["query_request"]["dataset_tags"].split(",") #configrecord
    has_tag = ""
    for k in required_tags_dict:
        if k in own_tags:
            has_tag=k
            break
            
    response_content = RecordDict({"query_response":ConfigRecord({"has_tag":has_tag})})
    return Message(response_content, reply_to=msg)

@app.train()
def train(msg: Message, context: Context):
    ndarrays = msg.content["arrays"].to_numpy_ndarrays()
    config = msg.content["config"]
    dataset_tag = config[str(context.node_id)]
    #get the data
    X,Y = retrieve_dataset(dataset_tag,"training")
    
    #create
    model = SGDRegressor()
    model.coef_ = ndarrays[0]
    model.intercept_ = ndarrays[1]
    
    #fit
    model.partial_fit(X, Y)
    
    #metrics calculation
    predictions = model.predict(X)
    local_loss = float(mean_squared_error(Y, predictions))
    num_samples = int(len(Y))
    
    
    updated_model = [model.coef_, model.intercept_]
    model_record = ArrayRecord(updated_model)
    
    #Send
    metrics_dict = {
        "loss": local_loss,
        "num-examples": num_samples,
    }
    metrics_record = MetricRecord(metrics_dict)
    content = RecordDict({
        "arrays": model_record, 
        "metrics": metrics_record
    })
    return Message(content=content, reply_to=msg)

@app.evaluate()
def evaluate(msg: Message, context: Context):
    ndarrays = msg.content["arrays"].to_numpy_ndarrays()
    config = msg.content["config"]
    dataset_tag = config[str(context.node_id)]
    X,Y = retrieve_dataset(dataset_tag,"evaluation")
    
    #Create from trained ndarrays
    model = SGDRegressor()
    model.coef_ = ndarrays[0]
    model.intercept_ = ndarrays[1]
    
    #predict on the evaluation set
    predictions = model.predict(X)
    
    #Metrics calculation
    eval_loss = float(mean_squared_error(Y, predictions))
    num_samples = int(len(Y))
    
    #send
    metrics_record = MetricRecord({
        "loss": eval_loss,
        "num-examples": num_samples,
    })
    content = RecordDict({"metrics": metrics_record})
    return Message(content=content, reply_to=msg)
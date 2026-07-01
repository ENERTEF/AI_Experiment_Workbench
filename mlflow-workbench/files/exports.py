import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any
from sklearn.metrics import mean_squared_error
from sklearn.linear_model import SGDRegressor
import mlflow
import os



def retrieve_dataset(dataset_tag,_for):
    fed_exp_id = os.environ["FEDERATED_EXPERIMENT_ID"]
    client = mlflow.tracking.MlflowClient()
    runs = client.search_runs(
        experiment_ids=[fed_exp_id],
        filter_string=f"attributes.run_name = '{dataset_tag}'",
        max_results=2
    )
    if len(runs) == 0:
        raise Exception('No associated run to dataset tag') 
    runs = [x for x in runs if x.inputs.dataset_inputs[0].tags[0].value == _for]
    if len(runs) == 0:
        raise f'No {dataset_tag} dataset with context {_for}'
    run = runs[0]
    if len(run.inputs.dataset_inputs) == 0:
        raise 'Input run corrupt: No dataset entries'
    dataset_info = run.inputs.dataset_inputs[0].dataset
    dataset_source = mlflow.data.get_source(dataset_info)
    file_path = dataset_source.load()
    import pandas as pd
    df = pd.read_csv(file_path,delimiter=";")
    return df


def train(
    init_weights: list[np.ndarray]
) -> Tuple[list[np.ndarray], Dict[str, Any]]:
    """
    Fits the local model using the provided training DataFrame.
    
    Args:
        df: The training dataset.
        init_weights: A list of numpy arrays representing [coefficients, intercept].
        
    Returns:
        A tuple containing:
            - updated_weights: list[np.ndarray] (the updated model parameters)
            - metrics: dict (e.g., {"loss": 0.123, "num-examples": 150})
    """
    df = retrieve_dataset("wine-quality","training")
    #Features
    X = df.drop(columns=["quality"]).to_numpy(dtype=np.float32)
    #Results
    Y = df["quality"].to_numpy(dtype=np.float32)
    model = SGDRegressor()
    model.coef_ = init_weights[0]
    model.intercept_ = init_weights[1]
    
    #fit
    model.partial_fit(X, Y)
    
    #metrics calculation
    predictions = model.predict(X)
    local_loss = float(mean_squared_error(Y, predictions))
    num_samples = int(len(Y))
    
    
    updated_model = [model.coef_, model.intercept_]
    
    #Send
    metrics_dict = {
        "loss": local_loss,
        "num-examples": num_samples,
    }
    return updated_model,metrics_dict
    

def evaluate(
    init_weights: list[np.ndarray]
) -> Dict[str, Any]:
    """
    Evaluates the global model using the provided validation DataFrame.
    
    Args:
        df: The evaluation dataset.
        init_weights: A list of numpy arrays representing [coefficients, intercept].
        
    Returns:
        A dictionary containing evaluation metrics (e.g., {"loss": 0.456, "num-examples": 50})
    """
    df = retrieve_dataset("wine-quality","evaluation")
    X = df.drop(columns=["quality"]).to_numpy(dtype=np.float32)
    #Results
    Y = df["quality"].to_numpy(dtype=np.float32)
    #Create from trained ndarrays
    model = SGDRegressor()
    model.coef_ = init_weights[0]
    model.intercept_ = init_weights[1]
    
    #predict on the evaluation set
    predictions = model.predict(X)
    
    #Metrics calculation
    eval_loss = float(mean_squared_error(Y, predictions))
    num_samples = int(len(Y))
    
    #send
    return {
        "loss": eval_loss,
        "num-examples": num_samples,
    }

DEPENDENCIES = [
    "pandas",
    "scikit-learn",
    "mlflow",
]

CAPABILITIES = {
    "dataset":"has$wine-quality"
}


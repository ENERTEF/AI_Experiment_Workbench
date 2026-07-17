import user.exports as exports
from flwr.app import ArrayRecord, Context, Message, MetricRecord, RecordDict,ConfigRecord
from flwr.clientapp import ClientApp
from flwr.common.logger import log
from pathlib import Path
import importlib.util
import os
from logging import INFO
app = ClientApp()

import abc

class cmpable(metaclass=abc.ABCMeta):
    @classmethod
    def __subclasshook__(cls, C):
        if cls is cmpable:
            # Check if the class defines greater-than and less-than operators
            if any("__lt__" in B.__dict__ for B in C.__mro__):
                return True
        return NotImplemented

def _CAPABILITIES():
    caps_path = Path("/etc/flower/capabilities.py")
    if not caps_path.exists():
        raise FileNotFoundError(
            "Missing required node-specific capabilities configuration file."
        )
        
    spec = importlib.util.spec_from_file_location("capabilities", caps_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec or loader for {caps_path}")
    
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "CAPABILITIES") or not callable(module.CAPABILITIES):
        raise AttributeError(
            f"The capabilities file at {caps_path} was loaded successfully, "
            f"but it is missing the required entrypoint: def CAPABILITIES(): ..."
        )
        
    result = module.CAPABILITIES()
    if not isinstance(result, dict):
        raise TypeError(
            f"CAPABILITIES() function inside {caps_path} "
            f"must return a dict, but got type {type(result).__name__}."
        )
    for key, value in result.items():
        if not isinstance(key, str):
            raise TypeError(f"Key {key} must be a string.") 
        if isinstance(value, cmpable):
            continue
        elif isinstance(value, (list, tuple, set)):
            for item in value:
                if not isinstance(item, cmpable):
                    raise TypeError(
                        f"Item {item} inside sequence {key} is not cmpable."
                    )        
        else:
            raise TypeError(
                f"Type {type(value).__name__} for key {key} is not cmpable "
                f"and cannot be parsed by the capability engine."
            )
    return result
        
def cast_check_primitive(x,y):
    try:
        if isinstance(x, bool):
            return y.lower() in ("true", "1")
        return type(x)(y)
    except (ValueError, TypeError) as cast_err:
        raise TypeError(
            f"Cannot cast incoming constraint value {y} "
            f"to match the Supernodes capability type {type(x).__name__}. Error: {cast_err}"
        )
        
def cast_check_composed(x,y):
    if len(x) > 0:
        try:
            return type(next(iter(x)))(y)
        except (ValueError, TypeError) as cast_err:
            raise TypeError(f"Cannot cast constraint {y} to match collection element type. Error: {cast_err}")
    

def op2fn(op:str):
    if op == "gt":
        return lambda x,y: x>cast_check_primitive(x,y)
    if op == "lt":
        return lambda x,y: x<cast_check_primitive(x,y)
    if op == "eq":
        return lambda x,y: x == cast_check_primitive(x,y)
    if op == "has":
        return lambda x,y: cast_check_composed(x,y) in x
    raise Exception(f"Unknown op: {op}")

@app.query()
def query(msg: Message, _: Context) -> Message:
    log(INFO, "Received config capability check request")
    config = msg.content["query_request"]
    eligible = True
    try:
        capabilities = _CAPABILITIES()
        for k, v in config.items():
            log(INFO, "Parsing capability constraint -> %s:%s", k, v)
            if k not in capabilities:
                log(INFO, "Capability validation failed: Node is missing key %s", k)
                eligible = False
                break
            op, value = v.split("$")
            cmp_fn = op2fn(op)
            eligible &= cmp_fn(capabilities[k], value)
            if not eligible:
                log(INFO, "Capability comparison failed for key %s with constraint %s", k, v)
                break
                
    except Exception as err:
        log(INFO, "Capability validation exception caught: %s. Defaulting eligible=False", str(err))
        eligible = False
        
    response_content = RecordDict({"query_response": ConfigRecord({"eligible": eligible})})
    return Message(response_content, reply_to=msg)

@app.train()
def train(msg: Message, _: Context):
    log(INFO, "Received train")
    ndarrays = msg.content["arrays"].to_numpy_ndarrays()
    updated_model,metrics_dict = exports.train(ndarrays)
    model_record = ArrayRecord(updated_model)
    
    metrics_record = MetricRecord(metrics_dict)
    content = RecordDict({
        "arrays": model_record, 
        "metrics": metrics_record
    })
    return Message(content=content, reply_to=msg)

@app.evaluate()
def evaluate(msg: Message, _: Context):
    log(INFO, "Received evaluate")
    ndarrays = msg.content["arrays"].to_numpy_ndarrays()
    metrics_dict = exports.evaluate(ndarrays)
    metrics_record = MetricRecord(metrics_dict)
    content = RecordDict({"metrics": metrics_record})
    return Message(content=content, reply_to=msg)
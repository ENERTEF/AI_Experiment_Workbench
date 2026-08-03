from typing import Any,Callable


class Capability:
    key:str
    value:str
    operation:str
    def __init__(self,key,value,operation):
        self.key = key
        self.value = value
        self.operation = operation
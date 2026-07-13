import operator
from typing_extensions import TypedDict, Annotated


class AgentState(TypedDict):
    #node message
    messages:Annotated[list, operator.add]
    #next node/cover
    next:str
from langchain_core.tools import tool
from agent_kernel.sub_agents.react_agent import ReactAgent


@tool
def calculator(expression: str) -> str:
    """执行数学计算，传入算式如 '2+3'、'10*5'"""
    try:
        return str(eval(expression))
    except Exception:
        return "计算失败，请检查表达式"


agent = ReactAgent(name="agent1", tools=[calculator])
build = agent.build_agent

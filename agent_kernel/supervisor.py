from langgraph.graph import StateGraph, START, END
from agent_kernel.config import init_model
from agent_kernel.state import AgentState
from agent_kernel.sub_agents.sub_agent1 import build as build_agent1
from agent_kernel.sub_agents.sub_agent2 import build as build_agent2
from agent_kernel.sub_agents.context import compress_node
from langchain_core.messages import SystemMessage
from agent_kernel.memory import memory_node, save_node

# ==== 定制化变量（按需修改）====

SUPERVISOR_PROMPT = ""

VALID_ROUTES = {"agent1", "agent2", "FINISH"}

# 路由映射表：supervisor 输出的 key → 注册的节点名
ROUTE_MAP = {
    "agent1": "agent1_node",
    "agent2": "agent2_node",
    "FINISH": END,
}

# ==== Supervisor 节点 ====

def supervisor_agent(state: AgentState):
    llm = init_model()
    messages = [SystemMessage(content=SUPERVISOR_PROMPT)] + state["messages"] if SUPERVISOR_PROMPT else state["messages"]
    resp = llm.invoke(messages)
    raw = resp.content.strip()
    first_word = raw.split("\n")[0].split()[0] if raw else ""
    first_word = first_word.strip("。，！？,.!?")
    if first_word not in VALID_ROUTES:
        first_word = "FINISH"
    return {"next": first_word}


def conditional_route(state: AgentState):
    return state["next"]


# ==== 构建主图 ====

def build_supervisor(checkpointer, store):
    builder = StateGraph(AgentState)

    # 基础设施节点
    builder.add_node("supervisor_agent", supervisor_agent)
    builder.add_node("memory_node", memory_node)
    builder.add_node("save_node", save_node)
    builder.add_node("compress_node", compress_node)

    # 注册子 Agent 节点
    builder.add_node("agent1_node", build_agent1())
    builder.add_node("agent2_node", build_agent2())

    # 流程：START → memory → supervisor → 路由分发
    builder.add_edge(START, "memory_node")
    builder.add_edge("memory_node", "supervisor_agent")
    builder.add_conditional_edges("supervisor_agent", conditional_route, ROUTE_MAP)

    # ReAct Agent 完成后 → save → compress → 回到 supervisor 继续
    builder.add_edge("agent1_node", "save_node")
    builder.add_edge("agent2_node", "save_node")
    builder.add_edge("save_node", "compress_node")
    builder.add_edge("compress_node", "supervisor_agent")

    return builder.compile(checkpointer=checkpointer, store=store)

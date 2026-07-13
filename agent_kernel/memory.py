from langgraph.store.memory import InMemoryStore
from agent_kernel.state import AgentState
from langchain_core.messages import SystemMessage, HumanMessage

# 全局长期记忆存储（跨会话持久化）
store = InMemoryStore()

# 注入到消息开头的记忆提示模板
MEMORY_PROMPT = ""


def _get_or_default(namespace: tuple, key: str, default):
    """从 store 读取记忆值，不存在时写入默认值并返回默认值。
    在 memory_node 中用于读取用户画像，在 save_node 中用于获取当前值。"""
    item = store.get(namespace, key)
    if item is not None:
        return item.value
    store.put(namespace, key, default)
    return default


# ---------- 用户画像提取（按需定制） ----------

def _extract_level(messages: list) -> str | None:
    """从本轮对话消息中提取用户水平等级。
    在 save_node 中被调用，用于更新长期记忆中的用户画像。"""
    ...


def _extract_interests(messages: list) -> list[str]:
    """从本轮对话消息中提取用户兴趣标签列表。
    在 save_node 中被调用，用于更新长期记忆中的用户画像。"""
    ...


def _extract_courses(messages: list) -> list[str]:
    """从本轮对话消息中提取用户已学课程列表。
    在 save_node 中被调用，用于更新长期记忆中的用户画像。"""
    ...


# ---------- Agent 图节点 ----------

def memory_node(state: AgentState) -> dict:
    """图入口节点：在 supervisor 路由前执行。
    从 store 读取该用户的长期记忆（水平/兴趣/已学课程），
    格式化为 SystemMessage 注入到消息列表开头，
    让后续子 Agent 感知用户背景。"""
    ...


def save_node(state: AgentState) -> dict:
    """图出口节点：在子 Agent 完成本轮回答后执行。
    从本轮对话消息中提取用户画像信息，
    去重合并写入 store，实现跨会话记忆累积。"""
    ...

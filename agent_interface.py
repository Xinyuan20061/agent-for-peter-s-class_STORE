from agent_kernel.supervisor import build_supervisor
from langgraph.checkpoint.memory import InMemorySaver
from agent_kernel.memory import store
from typing import AsyncIterator
from langchain_core.messages import HumanMessage


class AgentInterface:
    """后端调用 Agent 模块的唯一入口。"""

    # --- 节点 → 前端展示说明 ---
    # 前端可根据 event["node"] 区分思考过程与最终输出。
    # 注意：astream_events 追踪子图内部节点名，不是 supervisor 包装名。
    #
    # ReAct 子 Agent 的 token 流 = 思考过程（建议前端折叠展示）
    # 纯 LLM 节点的 token 流 = 最终回答（建议前端直接展示）
    # tools 节点 = 工具执行中（operation / tool_result）
    # compress_node = 系统消息（上下文已压缩，可静默或小字提示）

    def __init__(self):
        self.checkpointer = InMemorySaver()
        self.store = store
        self.graph = build_supervisor(checkpointer=self.checkpointer, store=self.store)

        # 内部节点：用户不需要看到它们产生的 token
        self._SKIP_NODES = {"supervisor_agent", "memory_node", "save_node"}

        # 工具名 → 用户可见的操作描述（按需扩展）
        self._TOOL_LABELS = {
            "calculator": "正在计算",
            "translator": "正在翻译",
        }

    async def _run_stream(
        self,
        message: str,
        user_id: str,
        thread_id: str,
    ) -> AsyncIterator[dict]:
        """
        流式对话接口，返回异步迭代器供后端通过 SSE 推送给前端。

        参数：
            message   (str)  用户输入的文本
            user_id   (str)  用户 ID
            thread_id (str)  会话 ID，用于隔离不同对话的短期记忆

        ── 事件协议（前端请按此解析）──

        公共字段：type (str) 事件类型，node (str) 来源节点名

        1. token — LLM 逐字输出（打字机效果）
            {"type": "token", "node": "xxx_agent", "content": "增量文本"}
            ReAct Agent 的 token → 思考过程，建议折叠
            纯 LLM 节点的 token → 最终回答，建议直接展示

        2. operation — 工具开始执行
            {"type": "operation", "node": "tools", "name": "操作名", "detail": {...}}
            前端建议：展示为 loading 状态提示

        3. tool_result — 工具执行完毕
            {"type": "tool_result", "node": "tools", "content": "工具返回文本"}
            前端建议：展示为可折叠引用块

        4. 流结束 — 后端自行追加 {"type": "done"}
        """

        input_data = {
            "messages": [HumanMessage(content=message)],
            "user_id": user_id,
        }

        config = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": user_id,
            }
        }

        async for event in self.graph.astream_events(input_data, config, version="v2"):
            kind = event["event"]

            # metadata.langgraph_node 才是真正的图节点名
            # event["name"] 在 LLM 事件中是模型类名（如 "ChatDeepSeek"），不能用于区分来源
            node = event["metadata"].get("langgraph_node", "")

            if node in self._SKIP_NODES:
                continue

            # LLM 每吐一个 token，触发一次 on_chat_model_stream
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if chunk.content:
                    yield {"type": "token", "content": chunk.content, "node": node}

            # 工具开始执行
            elif kind == "on_tool_start":
                name = event["name"]
                yield {
                    "type": "operation",
                    "name": self._TOOL_LABELS.get(name, name),
                    "detail": event["data"].get("input", {}),
                    "node": node,
                }

            # 工具执行完毕，结果作为 agent 的"思考依据"
            elif kind == "on_tool_end":
                output = event["data"].get("output", "")
                if output:
                    content = output.content if hasattr(output, "content") else str(output)
                    yield {"type": "tool_result", "content": content, "node": node}
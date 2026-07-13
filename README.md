# 🤖 ccAgent Template

> 基于 **LangGraph** 的轻量级多智能体模板框架，一行代码创建 ReAct 子 Agent，即插即用。

---

## 🧠 是什么

一套 **Supervisor + ReAct 子 Agent** 的标准工程模板。核心抽象 `ReactAgent` 类封装了 LangGraph 的 ToolNode + ReAct 循环，你只需：

1. 用 `@tool` 定义一个工具函数
2. `ReactAgent(name, tools)` 创建子 Agent
3. 在 `supervisor.py` 中注册路由

**10 行代码 = 一个完整的工具调用子 Agent。**

---

## 📁 项目结构

```
ccAgent_template/
├── agent_interface.py              # 🔌 对外入口，提供 SSE 流式接口
│
├── agent_kernel/                   # ⚙️ Agent 核心
│   ├── config.py                       # LLM 初始化（DeepSeek / 可替换）
│   ├── state.py                        # AgentState 类型定义
│   ├── memory.py                       # 长期记忆（Store 读写 + 用户画像模板）
│   ├── supervisor.py                   # 🧭 主图：Supervisor 路由编排
│   │
│   └── sub_agents/                     # 📦 子 Agent 集合
│       ├── react_agent.py                  # ⭐ ReactAgent 基类
│       ├── sub_agent1.py                   # 模板 1：计算器（单工具）
│       ├── sub_agent2.py                   # 模板 2：翻译器（单工具）
│       └── context.py                      # 上下文压缩
│
└── tools/                           # 🛠️ 工具目录（按需扩展）
    └── __init__.py
```

---

## 🔄 Agent 工作流

```
用户输入
  │
  ▼
memory_node          ← 加载长期记忆，注入用户画像
  │
  ▼
supervisor_agent     ← LLM 意图识别，输出路由 key
  │
  ├── "agent1" ──▶ agent1_node ──▶ tools ◀──┐
  │                    │             │       │  ReAct 循环
  │                    └─────────────┘       │
  │                                         │
  ├── "agent2" ──▶ agent2_node ──▶ tools    │
  │                    │             │       │
  │                    └─── ... ────────────┘
  │
  ├── "FINISH" ──▶ END
  │
  ▼
save_node             ← 提取本轮信息，更新长期记忆
  │
  ▼
compress_node         ← 超阈值时自动摘要压缩
  │
  ▼
supervisor_agent      ← 循环
```

| 组件 | 职责 |
|------|------|
| `supervisor_agent` | LLM 分析意图 → 输出路由词，分派子 Agent |
| `ReactAgent` | 思考 → 调工具 → 观察 → 回答，循环至完成 |
| `memory_node` | 会话开始时注入用户画像 `SystemMessage` |
| `save_node` | 会话结束时从对话中提取信息写入 Store |
| `compress_node` | Token 超 `MAX_TOKENS` 阈值时摘要旧消息 |

---

## ⭐ 核心：ReactAgent 基类

```python
# agent_kernel/sub_agents/react_agent.py

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from agent_kernel.state import AgentState
from agent_kernel.config import init_model

class ReactAgent:
    """ReAct Agent 工厂：name + tools → 编译后的子图"""

    def __init__(self, name: str, tools: list):
        self.name = name          # 节点名，supervisor 路由用
        self.tools = tools        # @tool 装饰的函数列表

    def build_agent(self):
        # 内部封装 ToolNode + agent_node + should_continue + 图编译
        ...
```

**设计要点：**
- `agent_node` 和 `should_continue` 作为闭包内嵌，实例间隔离
- `ToolNode` 自动管理工具调用/结果回传
- 返回 **编译好的子图**，直接挂到 supervisor

---

## 🚀 三步添加新 Agent

### Step 1 — 定义工具

```python
from langchain_core.tools import tool

@tool
def weather(city: str) -> str:
    """查询城市天气"""
    return f"{city}：晴，25°C"
```

### Step 2 — 创建子 Agent

```python
# agent_kernel/sub_agents/weather_agent.py

from langchain_core.tools import tool
from agent_kernel.sub_agents.react_agent import ReactAgent

@tool
def weather(city: str) -> str:
    """查询城市天气"""
    return f"{city}：晴，25°C"

agent = ReactAgent(name="weather", tools=[weather])
build = agent.build_agent
```

### Step 3 — 注册到 Supervisor

```python
# agent_kernel/supervisor.py

from agent_kernel.sub_agents.weather_agent import build as build_weather

SUPERVISOR_PROMPT = """分析意图，回复一个词：agent1 / agent2 / weather / FINISH"""

VALID_ROUTES = {"agent1", "agent2", "weather", "FINISH"}

ROUTE_MAP = {
    "agent1":  "agent1_node",
    "agent2":  "agent2_node",
    "weather": "weather_node",
    "FINISH":  END,
}

def build_supervisor(checkpointer, store):
    ...
    builder.add_node("weather_node", build_weather())       # 注册
    builder.add_edge("weather_node", "save_node")           # 出口
    ...
```

✅ 完成！新 Agent 已接入路由。

---

## 🔌 流式接口

```python
from agent_interface import AgentInterface

agent = AgentInterface()

async for event in agent._run_stream(
    message="3 加 5 等于多少？",
    user_id="user_1",
    thread_id="thread_1",
):
    match event["type"]:
        case "token":
            print(event["content"], end="")     # 🖨️ 打字机输出
        case "operation":
            print(f"\n[{event['name']}]")        # 🔧 工具调用中
        case "tool_result":
            print(f"\n📋 {event['content']}")    # 📊 工具返回结果
```

### 事件协议

| type | node | 含义 | 前端建议 |
|------|------|------|----------|
| `token` | `xxx_agent` | LLM 逐字输出 | ReAct → 折叠区 / 纯LLM → 主展示 |
| `operation` | `tools` | 工具开始执行 | Loading 状态提示 |
| `tool_result` | `tools` | 工具执行完毕 | 可折叠引用块 |

---

## 🛠️ 快速开始

### 环境

```bash
pip install langchain langgraph langchain-deepseek python-dotenv
```

### 配置 `.env`

```env
DEEPSEEK_API_KEY=sk-your-key
LLM_MODEL=deepseek-v4-pro
MAX_TOKENS=20000
```

### 运行测试

```python
import asyncio
from agent_interface import AgentInterface

async def main():
    agent = AgentInterface()
    async for e in agent._run_stream("你好，1+2=?", "u1", "t1"):
        if e["type"] == "token":
            print(e["content"], end="")
    print()

asyncio.run(main())
```

---

## 🧩 定制化变量速查

所有需要按项目定制的变量集中在 **`supervisor.py`** 顶部：

```python
SUPERVISOR_PROMPT = ""                              # 意图路由 prompt
VALID_ROUTES = {"agent1", "agent2", "FINISH"}        # 合法路由词
ROUTE_MAP = {                                        # 路由词 → 节点名
    "agent1": "agent1_node",
    "agent2": "agent2_node",
    "FINISH": END,
}
```

---

## 📦 技术栈

| 组件 | 用途 |
|------|------|
| [LangGraph](https://github.com/langchain-ai/langgraph) | 图编排、状态管理、条件路由 |
| [LangChain](https://github.com/langchain-ai/langchain) | LLM 调用、Tool 装饰器、消息格式 |
| DeepSeek | 默认底层模型（可替换为任意 LangChain 兼容模型） |
| InMemorySaver | 短期记忆，按 `thread_id` 隔离会话 |
| InMemoryStore | 长期记忆，跨会话持久化用户画像 |

---

## 📄 License

MIT — 自由使用，Happy Building! 🎉

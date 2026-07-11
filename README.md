# Agentic AI Learning Assistant — Agent 模块

基于 LangChain + LangGraph 的多智能体课程学习助手核心 Agent 模块，支持课程管理、概念讲解、学习规划和语义检索。

## 架构概览

```
agent/
├── agent_interface.py            # AgentInterface — 后端调用 Agent 的唯一入口
│
├── agent_kernel/                 # 核心模块
│   ├── config.py                     # LLM 初始化（DeepSeek）
│   ├── state.py                      # AgentState 定义
│   ├── memory.py                     # 长期记忆（LangGraph Store 读写 + 用户画像提取）
│   └── supervisor.py                 # 主图：Supervisor 路由编排
│
├── agents/                       # 子智能体
│   ├── course_agent.py               # 课程管理 ReAct Agent
│   ├── material_agent.py             # 资料管理 ReAct Agent
│   ├── concept_agent.py              # 概念讲解 ReAct Agent
│   ├── plan_agent.py                 # 学习规划 LLM Agent
│   ├── chat_agent.py                 # 闲聊 LLM Agent
│   └── context.py                    # 上下文压缩（超阈值自动摘要）
│
└── tools/                        # LangChain @tool 工具函数
    ├── course.py                     # 课程搜索/列表/创建
    ├── material.py                   # 资料搜索/添加/列表
    └── concept.py                    # 概念语义检索
```

## Agent 工作流

```
用户输入 → memory_node(加载用户画像) → supervisor(意图识别)
                                            │
         ┌───────┬────────┬────────┬───────┴──────┐
         ▼       ▼        ▼        ▼              ▼
      course  material  concept   plan           chat
     (ReAct)  (ReAct)   (ReAct)  (LLM)          (LLM)
         │       │        │        │              │
         └───────┴────────┴────────┘              ▼
                  │                             END
             save_node(更新用户画像)
                  │
           compress_node(超阈值时压缩上下文)
                  │
             supervisor → FINISH / 继续路由
```

| 组件 | 说明 |
|------|------|
| **Supervisor** | LLM 分析用户意图，分派到 5 个子智能体 |
| **ReAct 子智能体** | 思考 → 调工具 → 观察 → 回答，循环直到完成 |
| **长期记忆** | LangGraph Store，跨会话持久化用户画像（水平/兴趣/已学课程） |
| **短期记忆** | LangGraph InMemorySaver，按 thread_id 隔离不同对话 |
| **上下文压缩** | Token 超阈值时自动摘要旧消息 + 保留最近一轮对话 |

## 可用 Agent 工具

| 工具 | 所属智能体 | 功能 |
|------|-----------|------|
| `search_courses` | course | 按关键词搜索课程 |
| `list_all_courses` | course | 列出全部课程 |
| `create_course` | course | 创建新课程 |
| `search_materials` | material | 按课程名搜索学习资料 |
| `add_material` | material | 为课程添加学习资料（含自动分块+向量化） |
| `list_materials` | material | 列出所有课程的资料汇总 |
| `explain_concept` | concept | 语义检索概念解释（ChromaDB 向量搜索） |

## 快速开始

### 环境要求

- Python 3.10+
- MySQL 数据库
- DeepSeek API Key

### 安装

```bash
pip install langchain langgraph langchain-deepseek python-dotenv
```

### 环境变量

复制 `.env` 文件并填入你的配置：

```env
# Agent（必填）
DEEPSEEK_API_KEY=sk-xxx
LLM_MODEL=deepseek-v4-pro
MAX_TOKENS=20000

# 数据库（必填）
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/dbname

# 后端
SECRET_KEY=your-secret-key
```

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | 必填 |
| `LLM_MODEL` | 模型名称 | `deepseek-v4-pro` |
| `MAX_TOKENS` | 上下文压缩阈值（token 数） | `20000` |
| `DATABASE_URL` | MySQL 连接串 | 必填 |
| `SECRET_KEY` | JWT 签名密钥 | 必填 |
| `DEFAULT_USER_ID` | agent 工具默认用户 ID | `1` |

### 使用示例

```python
from app.agent.agent_interface import AgentInterface

agent = AgentInterface()

async for event in agent._run_stream(
    message="什么是机器学习",
    user_id="1",
    thread_id="t1"
):
    if event["type"] == "token":
        print(event["content"], end="")        # 打字机流式输出
    elif event["type"] == "operation":
        print(f"\n[{event['name']}]")           # 工具操作提示
    elif event["type"] == "tool_result":
        print(event["content"])                 # 工具返回结果
```

## 技术栈

| 组件 | 用途 |
|------|------|
| LangGraph | 图编排、状态管理、条件路由 |
| LangChain | LLM 调用、Tool 定义、消息格式 |
| DeepSeek | 底层大模型 |
| FastAPI | HTTP 接口（后端集成） |
| SQLAlchemy + MySQL | 数据持久化 |
| ChromaDB | 向量存储与语义检索 |
| sentence-transformers | 文本向量化 |
| InMemorySaver | 短期记忆（按 thread_id 隔离） |
| InMemoryStore | 长期记忆（跨会话用户画像） |

## 目录说明

本仓库为 Agent 核心模块，需配合 FastAPI 后端使用。完整的后端（含 API 路由、数据库模型、文件解析等）请参考主项目。

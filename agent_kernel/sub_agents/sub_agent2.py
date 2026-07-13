from langchain_core.tools import tool
from agent_kernel.sub_agents.react_agent import ReactAgent


@tool
def translator(text: str, target_lang: str = "英文") -> str:
    """翻译文本到目标语言"""
    mapping = {
        "你好": {"英文": "Hello", "日文": "こんにちは", "韩文": "안녕하세요"},
        "谢谢": {"英文": "Thank you", "日文": "ありがとう", "韩文": "감사합니다"},
        "再见": {"英文": "Goodbye", "日文": "さようなら", "韩文": "안녕히 가세요"},
    }
    result = mapping.get(text, {}).get(target_lang)
    if result:
        return result
    return f"「{text}」的{target_lang}翻译：{text}（模拟翻译，请替换为真实 API）"


agent = ReactAgent(name="agent2", tools=[translator])
build = agent.build_agent

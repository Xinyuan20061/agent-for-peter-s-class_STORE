from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from agent_kernel.state import AgentState
from agent_kernel.config import init_model

class ReactAgent:

    def __init__(self,name:str,tools:list):
        self.name=name
        self.tools=tools


    def build_agent(self):

        tool_node = ToolNode(self.tools)

        def agent_node(state: AgentState):
            # init model
            llm = init_model()
            llm = llm.bind_tools(self.tools)

            # get resp and return
            resp = llm.invoke(state["messages"])
            return {"messages": [resp]}

        def should_continue(state: AgentState):
            last_msg = state["messages"][-1]
            if last_msg.tool_calls:
                return "tools"
            return END

        builder = StateGraph(AgentState)

        builder.add_node(self.name, agent_node)
        builder.add_node("tools", tool_node)

        builder.add_edge(START, self.name)
        builder.add_conditional_edges(self.name, should_continue, {"tools": "tools", END: END})
        builder.add_edge("tools", self.name)

        return builder.compile()
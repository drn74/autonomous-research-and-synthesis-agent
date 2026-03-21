from langgraph.graph import StateGraph, START, END
from core.state import AgentState
from nodes.planner import planner_node
from nodes.crawler import crawler_node
from nodes.analyst import analyst_node
from nodes.synthesizer import synthesizer_node

def should_continue(state: AgentState) -> str:
    if state.get("is_saturated", False):
         return "synthesizer"
    return "crawler"

workflow = StateGraph(AgentState)

workflow.add_node("planner", planner_node)
workflow.add_node("crawler", crawler_node)
workflow.add_node("analyst", analyst_node)
workflow.add_node("synthesizer", synthesizer_node)

workflow.add_edge(START, "planner")
workflow.add_edge("planner", "crawler")
workflow.add_edge("crawler", "analyst")
workflow.add_conditional_edges("analyst", should_continue, {
    "crawler": "planner",
    "synthesizer": "synthesizer"
})
workflow.add_edge("synthesizer", END)

app = workflow.compile()

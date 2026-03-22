from langgraph.graph import StateGraph, START, END
from core.state import AgentState
from nodes.planner import planner_node
from nodes.crawler import crawler_node
from nodes.domain_detector import domain_detector_node
from nodes.site_spider import site_spider_node
from nodes.analyst import analyst_node
from nodes.synthesizer import synthesizer_node

def should_continue(state: AgentState) -> str:
    if state.get("is_saturated", False):
         return "synthesizer"
    return "crawler"

def route_after_detection(state: AgentState) -> str:
    if state.get("mode") == "deep_crawl":
        return "site_spider"
    return "analyst"

workflow = StateGraph(AgentState)

workflow.add_node("planner", planner_node)
workflow.add_node("crawler", crawler_node)
workflow.add_node("domain_detector", domain_detector_node)
workflow.add_node("site_spider", site_spider_node)
workflow.add_node("analyst", analyst_node)
workflow.add_node("synthesizer", synthesizer_node)

workflow.add_edge(START, "planner")
workflow.add_edge("planner", "crawler")
workflow.add_edge("crawler", "domain_detector")

workflow.add_conditional_edges("domain_detector", route_after_detection, {
    "site_spider": "site_spider",
    "analyst": "analyst"
})

workflow.add_edge("site_spider", "analyst")

workflow.add_conditional_edges("analyst", should_continue, {
    "crawler": "planner",
    "synthesizer": "synthesizer"
})
workflow.add_edge("synthesizer", END)

app = workflow.compile()

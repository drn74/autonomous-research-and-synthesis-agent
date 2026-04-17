from langgraph.graph import StateGraph, START, END
from core.state import AgentState
from core.config import APP_CONFIG
from nodes.planner import planner_node
from nodes.crawler import crawler_node
from nodes.domain_detector import domain_detector_node
from nodes.site_spider import site_spider_node
from nodes.analyst import analyst_node
from nodes.critic import critic_node

def route_after_critic(state: AgentState) -> str:
    """Decides whether to retry analysis or proceed to planner/end."""
    # Check for feedback loop
    if state.get("critic_feedback") and state.get("retry_count", 0) < 3:
        return "analyst"
        
    # Standard flow
    max_iterations = APP_CONFIG.get("max_iterations", 3)
    if state.get("is_saturated", False) or state.get("iteration", 0) >= max_iterations:
         return END
    if state.get("mode") == "archivist":
        return "site_spider"
    return "planner"

def route_after_detection(state: AgentState) -> str:
    if state.get("mode") == "deep_crawl" or state.get("mode") == "archivist":
        return "site_spider"
    return "analyst"

def route_start(state: AgentState) -> str:
    if state.get("mode") == "archivist":
        return "site_spider"
    return "planner"

workflow = StateGraph(AgentState)

workflow.add_node("planner", planner_node)
workflow.add_node("crawler", crawler_node)
workflow.add_node("domain_detector", domain_detector_node)
workflow.add_node("site_spider", site_spider_node)
workflow.add_node("analyst", analyst_node)
workflow.add_node("critic", critic_node)

workflow.add_conditional_edges(START, route_start, {
    "site_spider": "site_spider",
    "planner": "planner"
})

workflow.add_edge("planner", "crawler")
workflow.add_edge("crawler", "domain_detector")

workflow.add_conditional_edges("domain_detector", route_after_detection, {
    "site_spider": "site_spider",
    "analyst": "analyst"
})

workflow.add_edge("site_spider", "analyst")
workflow.add_edge("analyst", "critic")

workflow.add_conditional_edges("critic", route_after_critic, {
    "analyst": "analyst",
    "site_spider": "site_spider",
    "planner": "planner",
    END: END
})

app = workflow.compile()

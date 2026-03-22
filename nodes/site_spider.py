from core.state import AgentState
from core.config import console
from rich.panel import Panel

async def site_spider_node(state: AgentState) -> AgentState:
    console.print(Panel("[yellow]>>> SITE SPIDER NODE: (MOCK) Deep crawling activated...[/yellow]", border_style="yellow"))
    # The actual implementation will go here in Phase 4
    return state
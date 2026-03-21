import asyncio
from rich.panel import Panel
from core.config import console
from core.state import AgentState
from workflow import app

async def main():
    console.print(Panel.fit("[bold green]Starting ARSA LangGraph Orchestrator (Async)[/bold green]", border_style="green"))
    
    # EXAMPLE: Localized research
    initial_state = AgentState(
        topic="Cooking in Liguria in antiquity",
        goal="Create a historical guide on the ingredients, recipes, and culinary traditions of Liguria in ancient and Roman times.",
        language="Italian", # <--- NEW VARIABLE! You can set it to "English" for tech topics.
        queries=[],
        entities=[],
        iteration=0,
        saturation_score=0.0,
        notes_path=None,
        plan=None,
        is_saturated=False
    )

    console.print(f"[dim]Topic: {initial_state['topic']}[/dim]")
    console.print(f"[dim]Goal: {initial_state['goal']}[/dim]")
    console.print(f"[dim]Language: {initial_state['language']}[/dim]\n")

    try:
        final_state = await app.ainvoke(initial_state)
        console.print("\n[bold green]Graph completed![/bold green]")
    except Exception as e:
         console.print(f"\n[bold red]Error executing the graph: {e}[/bold red]")

if __name__ == "__main__":
    asyncio.run(main())
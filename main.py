import asyncio
from rich.panel import Panel
from core.config import console, APP_CONFIG
from core.state import AgentState
from workflow import app

async def main():
    console.print(Panel.fit("[bold green]Starting ARSA LangGraph Orchestrator (Async)[/bold green]", border_style="green"))
    
    # Load configuration from config.json
    initial_state = AgentState(
        topic=APP_CONFIG.get("topic", "Default Topic"),
        goal=APP_CONFIG.get("goal", "Default Goal"),
        language=APP_CONFIG.get("language", "English"),
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
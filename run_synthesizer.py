import asyncio
import warnings
from rich.panel import Panel

# Suppress annoying dependency warnings from requests
warnings.filterwarnings("ignore", message="urllib3 .* or chardet .* doesn't match a supported version!")

from core.config import console, APP_CONFIG
from core.state import AgentState
from nodes.synthesizer import synthesizer_node

async def main():
    console.print(Panel.fit("[bold green]Starting ARSA Synthesizer (Data Reporting)[/bold green]", border_style="green"))
    
    # Load configuration from config.json
    state = AgentState(
        topic=APP_CONFIG.get("topic", "Default Topic"),
        goal=APP_CONFIG.get("goal", "Default Goal"),
        language=APP_CONFIG.get("language", "English"),
        mode="normal",
        dense_domains=[],
        queries=[],
        entities=[],
        crawled_urls=[],
        iteration=0,
        saturation_score=1.0,
        notes_path=None,
        plan=None,
        is_saturated=True
    )

    console.print(f"[dim]Topic: {state['topic']}[/dim]")
    console.print(f"[dim]Goal: {state['goal']}[/dim]")
    console.print(f"[dim]Language: {state['language']}[/dim]\n")

    try:
        final_state = await synthesizer_node(state)
        console.print("\n[bold green]Synthesis phase completed successfully![/bold green]")
    except Exception as e:
         console.print(f"\n[bold red]Error executing the synthesizer: {e}[/bold red]")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import warnings
import argparse
from rich.panel import Panel

# Suppress annoying dependency warnings from requests
warnings.filterwarnings("ignore", message="urllib3 .* or chardet .* doesn't match a supported version!")

from core.config import console, APP_CONFIG
from core.state import AgentState
from nodes.synthesizer import synthesizer_node

async def main():
    parser = argparse.ArgumentParser(description="ARSA Synthesizer - Reporting Phase")
    parser.add_argument("--topic", type=str, help="Override the main topic")
    parser.add_argument("--goal", type=str, help="Override the goal")
    parser.add_argument("--lang", type=str, help="Override the language")
    args = parser.parse_args()

    console.print(Panel.fit("[bold green]Starting ARSA Synthesizer (Data Reporting)[/bold green]", border_style="green"))
    
    final_topic = args.topic if args.topic else APP_CONFIG.get("topic", "Default Topic")
    final_goal = args.goal if args.goal else APP_CONFIG.get("goal", "Default Goal")
    final_lang = args.lang if args.lang else APP_CONFIG.get("language", "English")

    # Load configuration from config.json or arguments
    state = AgentState(
        topic=final_topic,
        goal=final_goal,
        language=final_lang,
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

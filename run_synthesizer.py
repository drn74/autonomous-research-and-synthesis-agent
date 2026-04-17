import asyncio
import warnings
import argparse
from rich.panel import Panel

# Suppress annoying dependency warnings from requests
warnings.filterwarnings("ignore", message="urllib3 .* or chardet .* doesn't match a supported version!")

from core.config import console, APP_CONFIG
from core.state import AgentState
from nodes.synthesizer import synthesizer_node
from database.db_manager import get_last_session

async def main():
    parser = argparse.ArgumentParser(description="ARSA Synthesizer - Reporting Phase")
    parser.add_argument("--topic", type=str, help="Override the main topic")
    parser.add_argument("--goal", type=str, help="Override the goal")
    parser.add_argument("--lang", type=str, help="Override the language")
    parser.add_argument("--session-id", type=str, help="Target session ID to synthesize")
    args = parser.parse_args()

    console.print(Panel.fit("[bold green]Starting ARSA Synthesizer (Data Reporting)[/bold green]", border_style="green"))
    
    # 1. Determine session_id
    last_session = {}
    if not args.session_id:
        console.print("[dim]Looking for last session in database...[/dim]")
        last_session = get_last_session()
        session_id = last_session.get("session_id")
        if not session_id:
            console.print("[bold red]Error: No session found in database and --session-id not provided.[/bold red]")
            return
        console.print(f"[dim]Auto-detected last session: {session_id}[/dim]")
    else:
        session_id = args.session_id

    # 2. Set topic and goal (CLI override > DB session info > Config)
    final_topic = args.topic or last_session.get("topic") or APP_CONFIG.get("topic", "Default Topic")
    final_goal = args.goal or last_session.get("goal") or APP_CONFIG.get("goal", "Default Goal")
    final_lang = args.lang or APP_CONFIG.get("language", "English")

    # Load configuration from config.json or arguments
    state = AgentState(
        topic=final_topic,
        goal=final_goal,
        language=final_lang,
        session_id=session_id,
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

    console.print(f"[dim]Session ID: {state['session_id']}[/dim]")
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

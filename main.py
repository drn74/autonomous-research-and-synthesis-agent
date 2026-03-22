import asyncio
import os
import shutil
import warnings
from pathlib import Path
from rich.panel import Panel

# Suppress annoying dependency warnings from requests
warnings.filterwarnings("ignore", message="urllib3 .* or chardet .* doesn't match a supported version!")

from core.config import console, APP_CONFIG
from core.state import AgentState
from database.db_manager import clear_session
from workflow import app

async def main():
    console.print(Panel.fit("[bold green]Starting ARSA LangGraph Orchestrator (Async)[/bold green]", border_style="green"))
    
    # 1. Initialization and Cleanup
    session_id = "sess_001"
    if APP_CONFIG.get("clean_on_startup", True):
        console.print("[dim]Cleaning previous session data...[/dim]")
        # Clear database
        clear_session(session_id)
        # Clear data/raw folder
        raw_dir = Path("data/raw")
        if raw_dir.exists():
            for file in raw_dir.glob("*.md"):
                try:
                    file.unlink()
                except Exception as e:
                    console.print(f"[red]Could not delete {file.name}: {e}[/red]")

    # 2. Load configuration from config.json
    initial_state = AgentState(
        topic=APP_CONFIG.get("topic", "Default Topic"),
        goal=APP_CONFIG.get("goal", "Default Goal"),
        language=APP_CONFIG.get("language", "English"),
        queries=[],
        entities=[],
        crawled_urls=[],
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
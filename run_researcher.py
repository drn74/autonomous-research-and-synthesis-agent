import asyncio
import os
import shutil
import warnings
import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from rich.panel import Panel

# Suppress annoying dependency warnings from requests
warnings.filterwarnings("ignore", message="urllib3 .* or chardet .* doesn't match a supported version!")

from core.config import console, APP_CONFIG
from core.state import AgentState
from database.db_manager import clear_session, initialize_db, save_session
from workflow import app

async def main():
    parser = argparse.ArgumentParser(description="ARSA Researcher - Data Gathering Phase")
    parser.add_argument("--topic", type=str, help="The main topic of the research")
    parser.add_argument("--goal", type=str, help="The ultimate goal of the research guide")
    parser.add_argument("--lang", type=str, help="The target language for the research (e.g. English, Italian)")
    parser.add_argument("--synthesize", action="store_true", help="Automatically run the synthesizer after research")
    args = parser.parse_args()

    console.print(Panel.fit("[bold green]Starting ARSA LangGraph Researcher (Data Gathering)[/bold green]", border_style="green"))
    
    # 1. Initialization and DB setup
    session_id = f"sess_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    initialize_db()
    
    # 2. Load configuration: CLI args take precedence over config.json
    final_topic = args.topic if args.topic else APP_CONFIG.get("topic", "Default Topic")
    final_goal = args.goal if args.goal else APP_CONFIG.get("goal", "Default Goal")
    final_lang = args.lang if args.lang else APP_CONFIG.get("language", "English")

    save_session(session_id, final_topic, final_goal)

    if APP_CONFIG.get("clean_on_startup", False):
        console.print(f"[dim]Cleaning session data for {session_id}...[/dim]")
        clear_session(session_id)

    initial_state = AgentState(
        session_id=session_id,
        topic=final_topic,
        goal=final_goal,
        language=final_lang,
        mode="normal",
        dense_domains=[],
        queries=[],
        entities=[],
        crawled_urls=[],
        iteration=0,
        retry_count=0,
        saturation_score=0.0,
        notes_path=None,
        plan=None,
        is_saturated=False,
        critic_feedback=None
    )

    console.print(f"[dim]Session ID: {session_id}[/dim]")
    console.print(f"[dim]Topic: {initial_state['topic']}[/dim]")
    console.print(f"[dim]Goal: {initial_state['goal']}[/dim]")
    console.print(f"[dim]Language: {initial_state['language']}[/dim]\n")

    try:
        final_state = await app.ainvoke(initial_state)
        console.print("\n[bold green]Research phase completed successfully! All data is saved in SQLite and ChromaDB.[/bold green]")
        
        if args.synthesize:
            console.print("[bold yellow]Launching automatic RAG synthesis...[/bold yellow]")
            # Launch synthesizer for this specific session
            synth_args = [sys.executable, "run_synthesizer.py", "--session-id", session_id]
            if args.topic: synth_args.extend(["--topic", args.topic])
            if args.goal: synth_args.extend(["--goal", args.goal])
            if args.lang: synth_args.extend(["--lang", args.lang])
            
            subprocess.run(synth_args)
        else:
            console.print(f"[yellow]You can now run: python run_synthesizer.py --session-id {session_id}[/yellow]")
            
    except Exception as e:
         console.print(f"\n[bold red]Error executing the research graph: {e}[/bold red]")
         import traceback
         traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

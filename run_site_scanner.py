import asyncio
import os
import shutil
import warnings
import argparse
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse
from rich.panel import Panel
from rich.prompt import Confirm

# Suppress annoying dependency warnings from requests
warnings.filterwarnings("ignore", message="urllib3 .* or chardet .* doesn't match a supported version!")

from core.config import console, APP_CONFIG
from core.state import AgentState
from database.db_manager import clear_session, add_seed_url
from workflow import app

async def main():
    parser = argparse.ArgumentParser(description="ARSA Site Scanner - Archivist Mode")
    parser.add_argument("--url", type=str, required=True, help="The seed URL to start scanning from")
    parser.add_argument("--goal", type=str, help="The ultimate goal of the research guide")
    parser.add_argument("--lang", type=str, help="The target language for the research (e.g. English, Italian)")
    parser.add_argument("--max-pages", type=int, help="Maximum number of pages to crawl per domain")
    parser.add_argument("--max-depth", type=int, help="Maximum depth for BFS crawling")
    parser.add_argument("--synthesize", action="store_true", help="Automatically run the synthesizer after scanning")
    args = parser.parse_args()

    console.print(Panel.fit("[bold blue]Starting ARSA Site Scanner (Archivist Mode)[/bold blue]", border_style="blue"))
    
    # Update APP_CONFIG with CLI overrides if provided
    if args.max_pages:
        if "site_spider" not in APP_CONFIG: APP_CONFIG["site_spider"] = {}
        APP_CONFIG["site_spider"]["max_pages_per_domain"] = args.max_pages
    if args.max_depth:
        if "site_spider" not in APP_CONFIG: APP_CONFIG["site_spider"] = {}
        APP_CONFIG["site_spider"]["max_depth"] = args.max_depth

    session_id = "sess_001"
    
    # 1. Initialization and Cleanup
    if APP_CONFIG.get("clean_on_startup", True):
        console.print("[dim]Cleaning previous session data...[/dim]")
        clear_session(session_id)
        raw_dir = Path("data/raw")
        if raw_dir.exists():
            for file in raw_dir.glob("*.md"):
                try:
                    file.unlink()
                except Exception as e:
                    console.print(f"[red]Could not delete {file.name}: {e}[/red]")

    # 2. Add Seed URL to Database
    add_seed_url(session_id, args.url)
    
    # 3. Load configuration: CLI args take precedence over config.json
    final_goal = args.goal if args.goal else APP_CONFIG.get("goal", "Extract all relevant technical knowledge.")
    final_lang = args.lang if args.lang else APP_CONFIG.get("language", "English")
    
    domain_name = urlparse(args.url).netloc
    
    # Matching the structure expected by site_spider node
    dense_domains_init = [
        {
            "domain": domain_name,
            "url_count": 1,
            "type": "seed",
            "density_score": 1.0,
            "reasoning": "Seed URL provided for Archivist mode.",
            "entry_points": [args.url]
        }
    ]
    
    initial_state = AgentState(
        topic=f"Site Scan: {domain_name}",
        goal=final_goal,
        language=final_lang,
        mode="archivist",
        dense_domains=dense_domains_init,
        queries=[],
        entities=[],
        crawled_urls=[], # We haven't downloaded anything yet
        iteration=0,
        saturation_score=0.0,
        notes_path=None,
        plan=None,
        is_saturated=False
    )

    console.print(f"[dim]Seed URL: {args.url}[/dim]")
    console.print(f"[dim]Domain: {domain_name}[/dim]")
    console.print(f"[dim]Goal: {initial_state['goal']}[/dim]")
    console.print(f"[dim]Language: {initial_state['language']}[/dim]\n")

    try:
        # The workflow handles the loop between site_spider and analyst
        final_state = await app.ainvoke(initial_state)
        console.print("\n[bold green]Site scanning workflow completed![/bold green]")
        
        if args.synthesize:
            console.print("[bold yellow]Launching synthesizer...[/bold yellow]")
            # Pass relevant arguments to synthesizer
            synth_args = [sys.executable, "run_synthesizer.py"]
            if args.goal:
                synth_args.extend(["--goal", args.goal])
            if args.lang:
                synth_args.extend(["--lang", args.lang])
            
            subprocess.run(synth_args)
        else:
            console.print("[yellow]You can now run 'python run_synthesizer.py' to generate the final report.[/yellow]")
            
    except Exception as e:
         console.print(f"\n[bold red]Error executing the site scanner graph: {e}[/bold red]")
         import traceback
         traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

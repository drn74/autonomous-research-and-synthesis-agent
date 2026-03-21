import os
import json
from dotenv import load_dotenv
from rich.console import Console

# Load environment variables
load_dotenv()

# Global Rich Console for terminal output
console = Console()

# Verify critical API keys
if not os.getenv("GEMINI_API_KEY"):
    console.print("[bold red]WARNING: GEMINI_API_KEY not found in .env file[/bold red]")
if not os.getenv("SERPER_API_KEY"):
    console.print("[bold red]WARNING: SERPER_API_KEY not found in .env file[/bold red]")

# Load configuration from config.json
APP_CONFIG = {}
try:
    with open("config.json", "r", encoding="utf-8") as f:
        APP_CONFIG = json.load(f)
except Exception as e:
    console.print(f"[bold red]ERROR loading config.json: {e}[/bold red]")
    console.print("[yellow]Using fallback default configuration.[/yellow]")
    APP_CONFIG = {
        "topic": "Default Topic",
        "goal": "Default Goal",
        "language": "English",
        "max_iterations": 3,
        "saturation_threshold": 0.85,
        "models": {
            "planner": "gemini-2.5-flash",
            "analyst": "llama3.2:3b",
            "synthesizer": "gemini-2.5-flash"
        },
        "limits": {
            "max_search_results_per_query": 3,
            "max_chars_for_local_analysis": 6000,
            "max_chars_for_synthesis": 800000
        }
    }


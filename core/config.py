import os
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

import re
from pathlib import Path
from datetime import datetime
from core.state import AgentState
from core.config import console
from database.db_manager import get_entities_from_db
from langchain_google_genai import ChatGoogleGenerativeAI
from rich.panel import Panel
from nodes.crawler import sanitize_filename

async def synthesizer_node(state: AgentState) -> AgentState:
    console.print("\n[magenta]>>> SYNTHESIZER NODE: Generating the Final Guide...[/magenta]")
    
    session_mock = "sess_001"
    entities = get_entities_from_db(session_mock)
    
    raw_dir = Path("data/raw")
    all_content = ""
    file_count = 0
    
    if raw_dir.exists():
        for filepath in raw_dir.glob("*.md"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    file_text = f.read()
                    file_text = re.sub(r'\[Testo troncato.*', '', file_text) 
                    file_text = re.sub(r'\[...\]', '', file_text)
                    all_content += f"\n\n--- START DOCUMENT: {filepath.name} ---\n" + file_text
                    file_count += 1
            except Exception:
                pass
                
    max_chars_for_gemini = 800000
    if len(all_content) > max_chars_for_gemini:
        all_content = all_content[:max_chars_for_gemini]

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.3, 
        max_retries=2
    )

    prompt = f"""
    Act as a Senior Technical Writer and an Expert. 
    Based EXCLUSIVELY on the following research documents provided, write a comprehensive and in-depth guide to answer this GOAL:
    
    GOAL: {state['goal']}
    
    CRITICAL: The final guide MUST be written entirely in the "{state['language']}" language.
    
    WRITING GUIDELINES:
    1. The guide must be structured in logical chapters.
    2. Maintain a professional, authoritative, and objective tone.
    3. Use rich Markdown formatting (tables, bullet points, bold text).
    4. DO NOT mention the source documents ("as seen in document X"), synthesize the knowledge fluidly.
    
    RESEARCH DOCUMENTS:
    {all_content}
    """

    console.print("[cyan]Invoking Gemini (this might take a minute)...[/cyan]")
    
    try:
        response = await llm.ainvoke(prompt)
        final_text = response.content
    except Exception as e:
        console.print(f"[bold red]Fatal error in Gemini during synthesis:[/bold red] {e}")
        return state

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    slug_topic = sanitize_filename(state['topic'].lower()[:50])
    final_filepath = output_dir / f"FINAL_GUIDE_{slug_topic}.md"
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    frontmatter = f"""---
title: "{state['topic']}"
goal: "{state['goal']}"
language: "{state['language']}"
date_generated: "{current_date}"
sources_analyzed: {file_count}
entities_extracted: {len(entities)}
---

"""
    try:
        with open(final_filepath, "w", encoding="utf-8") as f:
            f.write(frontmatter + final_text)
            
        console.print(Panel(
            f"[bold green]🎉 RESEARCH SUCCESSFULLY COMPLETED! 🎉[/bold green]\n\n"
            f"Your definitive guide is ready in {state['language']}.\n"
            f"[yellow]File Saved in:[/yellow] {final_filepath}\n"
            f"[cyan]Sources used:[/cyan] {file_count}\n"
            f"[magenta]Entities discovered:[/magenta] {len(entities)}",
            title="ARSA Synthesizer", border_style="green"
        ))
    except Exception as e:
        console.print(f"[bold red]Error saving the final file:[/bold red] {e}")

    state["notes_path"] = str(final_filepath)
    return state

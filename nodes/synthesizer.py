import re
import asyncio
from pathlib import Path
from datetime import datetime
from core.state import AgentState
from core.config import console, APP_CONFIG
from core.llm import get_gemini_model
from database.db_manager import get_entities_from_db, sanitize_filename, get_knowledge_chunks
from rich.panel import Panel

async def synthesizer_node(state: AgentState) -> AgentState:
    console.print("\n[magenta]>>> SYNTHESIZER NODE: Aggregating and Structuring Raw Knowledge...[/magenta]")
    
    session_mock = "sess_001"
    
    # 1. Load Knowledge
    entities = get_entities_from_db(session_mock)
    chunks_data = get_knowledge_chunks(session_mock)
    
    # 2. Prepare the Executive Summary using Gemini
    llm = get_gemini_model(purpose="synthesizer", temperature=0.2)
    
    # Raccogliamo i titoli/url dei chunk per dare contesto a Gemini senza passargli megabyte di codice
    sources_summary = "\n".join(list(set([f"- {c['source_url']}" for c in chunks_data])))
    
    prompt = f"""
    Act as a Master Data Aggregator. Your task is to write a highly professional 'Executive Summary' for a research dossier.
    
    RESEARCH GOAL: {state['goal']}
    TARGET LANGUAGE: {state['language']}
    
    STATISTICS:
    - Entities Extracted: {len(entities)}
    - Knowledge Snippets Extracted: {len(chunks_data)}
    - Sources Analyzed: 
    {sources_summary[:2000]}
    
    INSTRUCTIONS:
    1. Write a 2-3 paragraph Executive Summary explaining what kind of data was collected and how it addresses the Research Goal.
    2. Write a brief 'Taxonomy' or categorization of the topics covered.
    3. Ensure the output is entirely in "{state['language']}".
    4. Do NOT attempt to write the whole manual, just the summary and introduction.
    """
    
    console.print("[dim]Invoking Gemini for Executive Summary...[/dim]")
    try:
        response = await llm.ainvoke(prompt)
        executive_summary = response.content.strip()
    except Exception as e:
        console.print(f"[red]Error generating summary: {e}[/red]")
        executive_summary = "Error generating executive summary."

    # 3. Build the Final Knowledge Dossier
    console.print("[dim]Compiling the final Knowledge Dossier...[/dim]")
    
    final_book_content = f"# Executive Summary\n\n{executive_summary}\n\n"
    final_book_content += "---\n\n# 1. Extracted Entities (Taxonomy)\n\n"
    
    # Group entities roughly alphabetically or just list them cleanly
    valid_entities = sorted([e for e in entities if len(e) > 2])
    final_book_content += ", ".join(valid_entities) + "\n\n"
    
    final_book_content += "---\n\n# 2. Raw Knowledge Chunks (Snippets, Code, Recipes)\n\n"
    final_book_content += "*This section contains the pure, unmodified technical data extracted during the research.*\n\n"
    
    # Group chunks by source URL
    chunks_by_source = {}
    for c in chunks_data:
        url = c['source_url']
        if url not in chunks_by_source:
            chunks_by_source[url] = []
        chunks_by_source[url].append(c)
        
    for url, chunks in chunks_by_source.items():
        final_book_content += f"## Source: {url}\n\n"
        for i, chunk in enumerate(chunks):
            content = chunk['content'].strip()
            # If it looks like code and doesn't have markdown blocks, wrap it
            if chunk['content_type'] == 'code' and not content.startswith('```'):
                content = f"```\n{content}\n```"
            
            final_book_content += f"### Snippet {i+1} ({chunk['content_type'].upper()})\n\n{content}\n\n"

    # 4. Output Finalization
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    slug_topic = sanitize_filename(state['topic'].lower()[:50])
    final_filepath = output_dir / f"KNOWLEDGE_DOSSIER_{slug_topic}.md"
    
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    frontmatter = f"""---
title: "{state['topic']}"
goal: "{state['goal']}"
language: "{state['language']}"
date_generated: "{current_date}"
knowledge_chunks_extracted: {len(chunks_data)}
entities_extracted: {len(entities)}
type: "Raw Knowledge Dossier"
---

"""
    try:
        with open(final_filepath, "w", encoding="utf-8") as f:
            f.write(frontmatter + final_book_content)
            
        console.print(Panel(
            f"[bold green]🎉 KNOWLEDGE DOSSIER COMPLETED! 🎉[/bold green]\n\n"
            f"All raw data and snippets have been safely aggregated.\n"
            f"[yellow]File Saved in:[/yellow] {final_filepath}\n"
            f"[cyan]Snippets preserved:[/cyan] {len(chunks_data)}\n"
            f"[magenta]File size:[/magenta] {final_filepath.stat().st_size / 1024:.2f} KB",
            title="ARSA Data Aggregator", border_style="green"
        ))
    except Exception as e:
        console.print(f"[bold red]Error saving file:[/bold red] {e}")

    state["notes_path"] = str(final_filepath)
    return state

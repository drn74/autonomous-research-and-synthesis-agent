import re
import asyncio
import json
from pathlib import Path
from datetime import datetime
from core.state import AgentState
from core.config import console, APP_CONFIG
from core.llm import get_gemini_model
from database.db_manager import get_entities_from_db, sanitize_filename
from database.vector_manager import VectorManager
from rich.panel import Panel
from langchain_core.messages import HumanMessage

async def synthesizer_node(state: AgentState) -> AgentState:
    console.print("\n[magenta]>>> SYNTHESIZER NODE: Generating RAG-based Research Dossier...[/magenta]")
    
    session_id = state["session_id"]
    vector_db = VectorManager()
    
    # 1. Load Entities
    entities = get_entities_from_db(session_id)
    if not entities:
        console.print("[bold red]ERRORE: Nessuna entità trovata nel DB per questa sessione.[/bold red]")
        return state

    llm = get_gemini_model(purpose="synthesizer", temperature=0.2)
    
    # 2. Plan the Dossier Structure (Chapters)
    console.print("[dim]Planning dossier structure based on identified entities...[/dim]")
    entities_sample = ", ".join(sorted(entities)[:50])
    
    plan_prompt = f"""
    Based on the following technical entities extracted during research, propose a 4-5 chapter structure for a professional research dossier.
    
    RESEARCH GOAL: "{state['goal']}"
    TOPIC: "{state['topic']}"
    ENTITIES: {entities_sample}
    
    OUTPUT INSTRUCTIONS:
    - Respond ONLY with a JSON list of strings (chapter titles).
    - Example: ["Chapter 1: Title", "Chapter 2: Title", ...]
    
    CHAPTER PLAN:
    """
    
    try:
        plan_response = await llm.ainvoke([HumanMessage(content=plan_prompt)])
        chapters = json.loads(re.search(r'\[.*\]', plan_response.content, re.DOTALL).group(0))
    except Exception as e:
        console.print(f"[yellow]Warning: Could not generate plan, using default structure. Error: {e}[/yellow]")
        chapters = ["Technical Overview", "Detailed Procedures", "Key Components", "Summary of Findings"]

    # 3. Generate Content for each Chapter using RAG
    dossier_sections = []
    total_sources = set()
    
    for i, chapter in enumerate(chapters):
        console.print(f"  [cyan]Generating {chapter} (RAG query)...[/cyan]")
        
        # Semantic search for the chapter
        relevant_docs = vector_db.query(session_id, chapter, n_results=8)
        
        if not relevant_docs:
            continue
            
        # Prepare context for Gemini
        context_blocks = []
        for doc in relevant_docs:
            source = doc.metadata.get("source_url", "Unknown Source")
            total_sources.add(source)
            context_blocks.append(f"SOURCE: {source}\nCONTENT: {doc.page_content}")
            
        context_text = "\n---\n".join(context_blocks)
        
        chapter_prompt = f"""
        Write the content for the following chapter of a research dossier.
        
        CHAPTER TITLE: "{chapter}"
        RESEARCH GOAL: "{state['goal']}"
        TARGET LANGUAGE: "{state['language']}"
        
        CONTEXT DATA (from research):
        {context_text[:15000]}
        
        INSTRUCTIONS:
        1. Synthesize the context data into a professional and detailed report for this chapter.
        2. Use CITATIONS: whenever you use information from a source, mention the source URL in brackets, e.g., [https://example.com].
        3. Be technical and precise. Preserving code snippets if they are relevant to this chapter.
        4. Write the entire content in "{state['language']}".
        5. Do NOT use introductory filler like "Here is the content for...".
        
        CHAPTER CONTENT:
        """
        
        try:
            chapter_response = await llm.ainvoke([HumanMessage(content=chapter_prompt)])
            dossier_sections.append(f"# {chapter}\n\n{chapter_response.content.strip()}")
        except Exception as e:
            console.print(f"[red]Error generating chapter {chapter}: {e}[/red]")

    # 4. Generate Executive Summary
    summary_prompt = f"""
    Write a professional Executive Summary for the following research dossier.
    
    TOPIC: "{state['topic']}"
    GOAL: "{state['goal']}"
    LANGUAGE: "{state['language']}"
    CHAPTERS COVERED: {", ".join(chapters)}
    
    INSTRUCTIONS:
    - Focus on the main takeaways and how the goal was achieved.
    - Write 2-3 paragraphs.
    - Respond in "{state['language']}".
    """
    
    try:
        summary_response = await llm.ainvoke([HumanMessage(content=summary_prompt)])
        executive_summary = summary_response.content.strip()
    except:
        executive_summary = "Dossier generated using RAG synthesis."

    # 5. Final Compilation
    full_content = f"# Executive Summary\n\n{executive_summary}\n\n"
    full_content += "\n\n---\n\n".join(dossier_sections)
    
    # 6. Output Finalization
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    slug_topic = sanitize_filename(state['topic'].lower()[:50])
    final_filepath = output_dir / f"RAG_DOSSIER_{slug_topic}.md"
    
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    frontmatter = f"""---
title: "{state['topic']}"
goal: "{state['goal']}"
language: "{state['language']}"
date_generated: "{current_date}"
type: "RAG-Synthesized Knowledge Dossier"
sources_analyzed: {len(total_sources)}
chapters_count: {len(chapters)}
---

"""
    try:
        with open(final_filepath, "w", encoding="utf-8") as f:
            f.write(frontmatter + full_content)
            
        console.print(Panel(
            f"[bold green]🚀 RAG DOSSIER COMPLETED! 🚀[/bold green]\n\n"
            f"Synthesized from {len(total_sources)} sources using vector search.\n"
            f"[yellow]File Saved in:[/yellow] {final_filepath}\n"
            f"[cyan]Chapters generated:[/cyan] {len(dossier_sections)}",
            title="ARSA RAG Synthesizer", border_style="green"
        ))
    except Exception as e:
        console.print(f"[bold red]Error saving file:[/bold red] {e}")

    state["notes_path"] = str(final_filepath)
    return state

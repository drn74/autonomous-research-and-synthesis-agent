import os
import json
import sqlite3
import asyncio
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import List, TypedDict, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
import aiohttp

# Import for Crawl4AI
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

# --- Initialization ---
load_dotenv()
console = Console()

# Make sure you have API Keys in .env
# GEMINI_API_KEY="Your_Key"
# SERPER_API_KEY="Your_Serper_Key"

# --- 1. State Definition (AgentState) ---
class AgentState(TypedDict):
    topic: str
    goal: str
    language: str # New language variable (e.g., "en", "it")
    queries: List[str]
    entities: List[str]
    iteration: int
    saturation_score: float
    notes_path: Optional[str]
    plan: Optional[str]
    is_saturated: bool

# --- 2. Pydantic Schemas for Structured Output (Gemini) ---
class PlannerOutput(BaseModel):
    plan_outline: str = Field(description="A textual draft of the work plan or chapters of the final document.")
    new_queries: List[str] = Field(description="List of 3-5 new specific search queries to expand the topic.")
    new_entities_to_track: List[str] = Field(description="Key entities (people, concepts, technologies) just identified to track.")
    saturation_estimate: float = Field(description="A score from 0.0 to 1.0 indicating how much the current entities cover the Goal. 1.0 = Topic completely covered.")

# --- Helper: Database Connection ---
DB_PATH = "research.db"

def get_wsl_host_ip() -> str:
    """Returns localhost since we verified Ollama listens there."""
    return "127.0.0.1"

def get_entities_from_db(session_id: str) -> List[str]:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM entities WHERE session_id = ?", (session_id,))
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]
    except Exception as e:
        console.print(f"[bold red]DB Error (get_entities): {e}[/bold red]")
        return []

def save_entities_to_db(session_id: str, entities: List[str]):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        for entity in entities:
            cursor.execute('''
                INSERT OR IGNORE INTO entities (session_id, name, entity_type) 
                VALUES (?, ?, 'Concept')
            ''', (session_id, entity))
        conn.commit()
        conn.close()
    except Exception as e:
        console.print(f"[bold red]DB Error (save_entities): {e}[/bold red]")

def get_url_hash(url: str) -> str:
    return hashlib.md5(url.encode('utf-8')).hexdigest()

def is_url_crawled(url: str) -> bool:
    url_hash = get_url_hash(url)
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM crawled_urls WHERE url_hash = ?", (url_hash,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    except Exception as e:
        console.print(f"[bold red]DB Error (is_url_crawled): {e}[/bold red]")
        return False

def save_crawled_url(url: str, session_id: str, local_path: str):
    url_hash = get_url_hash(url)
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("ALTER TABLE crawled_urls ADD COLUMN status TEXT DEFAULT 'pending_analysis'")
            cursor.execute("ALTER TABLE crawled_urls ADD COLUMN local_path TEXT")
        except sqlite3.OperationalError:
            pass
            
        cursor.execute('''
            INSERT OR REPLACE INTO crawled_urls (url_hash, url, session_id, status, local_path)
            VALUES (?, ?, ?, 'pending_analysis', ?)
        ''', (url_hash, url, session_id, str(local_path)))
        conn.commit()
        conn.close()
    except Exception as e:
        console.print(f"[bold red]DB Error (save_crawled_url): {e}[/bold red]")

def get_pending_files(session_id: str) -> List[tuple]:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT url_hash, local_path FROM crawled_urls WHERE session_id = ? AND status = 'pending_analysis'", (session_id,))
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        console.print(f"[bold red]DB Error (get_pending_files): {e}[/bold red]")
        return []
        
def mark_file_analyzed(url_hash: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE crawled_urls SET status = 'analyzed' WHERE url_hash = ?", (url_hash,))
        conn.commit()
        conn.close()
    except Exception as e:
        console.print(f"[bold red]DB Error (mark_file_analyzed): {e}[/bold red]")

# --- Helper: Serper.dev Search ---
async def web_search(queries: List[str]) -> List[str]:
    serper_api_key = os.getenv("SERPER_API_KEY")
    if not serper_api_key:
        console.print("[bold red]ERROR: SERPER_API_KEY not found in .env file[/bold red]")
        return []
    
    urls = []
    async with aiohttp.ClientSession() as session:
        for query in queries:
            try:
                payload = json.dumps({"q": query, "num": 3})
                headers = {
                    'X-API-KEY': serper_api_key,
                    'Content-Type': 'application/json'
                }
                async with session.post("https://google.serper.dev/search", headers=headers, data=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        organic_results = data.get("organic", [])
                        for result in organic_results:
                            link = result.get("link")
                            if link:
                                urls.append(link)
                    else:
                        console.print(f"[red]Serper API Error: {response.status}[/red]")
            except Exception as e:
                console.print(f"[red]Error during search for '{query}': {e}[/red]")
    
    return list(set(urls))

def sanitize_filename(name: str) -> str:
    return re.sub(r'[^\w\-_\. ]', '_', name)

# --- 3. Graph Nodes ---

async def planner_node(state: AgentState) -> AgentState:
    console.print(Panel(f"[bold cyan]Planning in progress...[/bold cyan]\nLanguage: {state['language'].upper()}\nTopic: {state['topic']}", border_style="cyan"))
    
    session_mock = "sess_001"
    db_entities = get_entities_from_db(session_mock)
    all_entities = list(set(state.get("entities", []) + db_entities))

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.2,
        max_retries=2
    )
    
    structured_llm = llm.with_structured_output(PlannerOutput)

    prompt = f"""
    You are an AI Research Planner. Your goal is to analyze the Topic and the Goal, 
    evaluate the current knowledge (Entities already found) and generate the next actions.
    
    CRITICAL: The target language for the research is "{state['language']}".
    You MUST generate the 'new_queries' strictly in "{state['language']}" to ensure search engines find localized content.
    The 'plan_outline' and 'new_entities_to_track' should also be in "{state['language']}".

    TOPIC: {state['topic']}
    GOAL: {state['goal']}
    ENTITIES ALREADY FOUND: {', '.join(all_entities) if all_entities else 'None, we are starting.'}
    CURRENT PLAN: {state.get('plan', 'None')}

    TASK:
    1. Generate or update a 'plan_outline' that structures how to reach the Goal.
    2. Identify 3-5 precise search queries ('new_queries') to fill the current knowledge gaps. 
    3. Extract 'new_entities_to_track' that are mentioned in the plan or Goal but have not been searched.
    4. Estimate saturation ('saturation_estimate' 0.0 - 1.0). 1.0 = Topic completely covered.
    """

    console.print("[dim]Invoking Gemini 2.0 Flash (Planner)...[/dim]")
    
    try:
        result: PlannerOutput = await structured_llm.ainvoke(prompt)
    except Exception as e:
        console.print(f"[bold red]LLM Error:[/bold red] {e}")
        return state

    console.print(Panel(
        f"[green]Generated Queries ({state['language']}):[/green]\n- " + "\n- ".join(result.new_queries) +
        f"\n\n[yellow]New Entities:[/yellow] {', '.join(result.new_entities_to_track)}" +
        f"\n\n[magenta]Estimated Saturation:[/magenta] {result.saturation_estimate}",
        title="Planner Result", border_style="green"
    ))

    save_entities_to_db(session_mock, result.new_entities_to_track)

    new_iteration = state["iteration"] + 1
    
    is_saturated = False
    if result.saturation_estimate >= 0.9 or new_iteration > 2: 
        is_saturated = True
        console.print("[bold red]WARNING: Saturation reached or Iteration limit exceeded![/bold red]")

    return {
        "topic": state["topic"],
        "goal": state["goal"],
        "language": state["language"],
        "queries": result.new_queries,
        "entities": list(set(all_entities + result.new_entities_to_track)),
        "iteration": new_iteration,
        "saturation_score": result.saturation_estimate,
        "notes_path": state.get("notes_path"),
        "plan": result.plan_outline,
        "is_saturated": is_saturated
    }

async def crawler_node(state: AgentState) -> AgentState:
    console.print(f"\n[yellow]>>> CRAWLER NODE: Searching URLs for {len(state['queries'])} queries...[/yellow]")
    
    if not state['queries']:
        return state

    new_urls = await web_search(state['queries'])
    console.print(f"[dim]Found {len(new_urls)} unique URLs.[/dim]")
    
    urls_to_crawl = [url for url in new_urls if not is_url_crawled(url)]
    console.print(f"[cyan]URLs to download: {len(urls_to_crawl)}[/cyan]")
    
    if not urls_to_crawl:
        return state

    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    session_mock = "sess_001"

    browser_config = BrowserConfig(headless=True)
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            crawl_task = progress.add_task("[cyan]Crawling URLs...", total=len(urls_to_crawl))
            
            for url in urls_to_crawl:
                progress.update(crawl_task, description=f"[cyan]Downloading: {url[:60]}...[/cyan]")
                try:
                    result = await crawler.arun(url=url, config=run_config)
                    if result.success:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        slug = sanitize_filename(url.split('//')[-1][:40])
                        filename = f"{timestamp}_{slug}.md"
                        filepath = raw_dir / filename
                        
                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(f"---\nurl: {url}\ntimestamp: {timestamp}\n---\n\n")
                            content = result.markdown if hasattr(result, 'markdown') else str(result.html)
                            f.write(content)
                            
                        save_crawled_url(url, session_mock, str(filepath))
                        progress.console.print(f"[green]✓ Success:[/green] {filename} saved.")
                    else:
                        progress.console.print(f"[red]✗ Failed:[/red] {url}")
                except Exception as e:
                     pass
                finally:
                    progress.advance(crawl_task)

    return state

async def run_local_analysis(file_path: str, goal: str, wsl_ip: str, language: str) -> dict:
    import time
    import re
    start_time = time.time()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return {"error": f"File read error: {e}"}

    max_chars = 6000 
    if len(content) > max_chars:
        content = content[:max_chars] + "\n\n[...]"

    # Prompt remains in English for LLM stability, but acknowledges the text language
    prompt = f"""
You are a data extractor. Your task is to identify key entities, concepts, and names from the text below.
The text you are reading might be in "{language}" language. 
The Goal of the research is: {goal}

Instructions:
1. Return ONLY a JSON object with a list of up to 10 entities extracted from the text.
2. Ensure the JSON structure and keys are in English (e.g. {{"entities": [...]}}), but the extracted values should remain in their original language.
3. DO NOT answer questions in the text.
4. If no relevant entities are found, return an empty list.

Example Output: {{"entities": ["Entity1", "Entity2"]}}

TEXT TO ANALYZE:
\"\"\"
{content}
\"\"\"

JSON RESPONSE:
"""

    ollama_url = f"http://{wsl_ip}:11434/api/generate"
    payload = {
        "model": "llama3.2:3b",
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_ctx": 4096,
            "num_predict": 512
        }
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(ollama_url, json=payload, timeout=120) as response:
                if response.status == 200:
                    data = await response.json()
                    result_text = data.get("response", "").strip()
                    
                    try:
                        match = re.search(r'\{.*\}', result_text, re.DOTALL)
                        if match:
                            json_str = match.group(0)
                        else:
                            if result_text.startswith('{') and not result_text.endswith('}'):
                                json_str = result_text + '"]}' if '"entities"' in result_text else result_text + '}'
                            else:
                                json_str = result_text

                        parsed_json = json.loads(json_str)
                        return {
                            "entities": parsed_json.get("entities", []),
                            "inference_time": time.time() - start_time
                        }
                    except Exception:
                        return {"error": f"JSON parsing error."}
                else:
                    return {"error": f"API Error: {response.status}"}
        except Exception as e:
            return {"error": str(e)}

async def analyst_node(state: AgentState) -> AgentState:
    console.print("\n[blue]>>> ANALYST NODE: Analyzing results with Ollama (Llama 3.2)...[/blue]")
    
    session_mock = "sess_001"
    pending_files = get_pending_files(session_mock)
    
    if not pending_files:
        console.print("[yellow]No new files to analyze.[/yellow]")
        return state

    wsl_ip = get_wsl_host_ip()

    new_entities_found = set()
    
    for url_hash, local_path in pending_files:
        if not local_path:
             mark_file_analyzed(url_hash)
             continue
             
        filename = Path(local_path).name
        console.print(f"[cyan]Analysis in progress:[/cyan] {filename}")
        
        # Pass the language from the state to the analysis function
        result = await run_local_analysis(local_path, state['goal'], wsl_ip, state['language'])
        
        if "error" in result:
             console.print(f"[red]Error during analysis of {filename}: {result['error']}[/red]")
             continue
             
        entities = result.get("entities", [])
        inf_time = result.get("inference_time", 0.0)
        
        valid_entities = [e for e in entities if e and isinstance(e, str) and len(e) < 50]
        
        console.print(Panel(
            f"[green]File:[/green] {filename}\n"
            f"[yellow]Extracted entities:[/yellow] {len(valid_entities)}\n"
            f"[magenta]GPU inference time:[/magenta] {inf_time:.2f}s",
            title="Local LLM Result", border_style="blue"
        ))
        
        if valid_entities:
            save_entities_to_db(session_mock, valid_entities)
            new_entities_found.update(valid_entities)
            
        mark_file_analyzed(url_hash)

    all_db_entities = get_entities_from_db(session_mock)
    unique_entities_count = len(all_db_entities)
    calculated_saturation = min(unique_entities_count / 50.0, 1.0)
    
    console.print(f"\n[bold blue]Total unique entities in DB:[/bold blue] {unique_entities_count}")
    console.print(f"[bold magenta]New Saturation Score calculated:[/bold magenta] {calculated_saturation:.2f}")

    is_saturated = False
    if calculated_saturation >= 0.85:
        is_saturated = True
        console.print("[bold red]WARNING: Saturation reached via local analysis![/bold red]")

    return {
        "topic": state["topic"],
        "goal": state["goal"],
        "language": state["language"],
        "queries": state["queries"],
        "entities": list(set(state.get("entities", []) + list(new_entities_found))),
        "iteration": state["iteration"],
        "saturation_score": calculated_saturation,
        "notes_path": state.get("notes_path"),
        "plan": state.get("plan"),
        "is_saturated": is_saturated
    }

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

def should_continue(state: AgentState) -> str:
    if state.get("is_saturated", False):
         return "synthesizer"
    return "crawler"

workflow = StateGraph(AgentState)
workflow.add_node("planner", planner_node)
workflow.add_node("crawler", crawler_node)
workflow.add_node("analyst", analyst_node)
workflow.add_node("synthesizer", synthesizer_node)

workflow.add_edge(START, "planner")
workflow.add_edge("planner", "crawler")
workflow.add_edge("crawler", "analyst")
workflow.add_conditional_edges("analyst", should_continue, {
    "crawler": "planner",
    "synthesizer": "synthesizer"
})
workflow.add_edge("synthesizer", END)

app = workflow.compile()

async def main():
    console.print(Panel.fit("[bold green]Starting ARSA LangGraph Orchestrator (Async)[/bold green]", border_style="green"))
    
    # EXAMPLE: Localized research
    initial_state = AgentState(
        topic="Cooking in Liguria in antiquity",
        goal="Create a historical guide on the ingredients, recipes, and culinary traditions of Liguria in ancient and Roman times.",
        language="Italian", # <--- NEW VARIABLE! You can set it to "English" for tech topics.
        queries=[],
        entities=[],
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
import time
import re
import json
import aiohttp
from pathlib import Path
from core.state import AgentState
from core.config import console, APP_CONFIG
from database.db_manager import get_wsl_host_ip, get_pending_files, mark_file_analyzed, save_entities_to_db, get_entities_from_db, save_knowledge_chunk
from rich.panel import Panel

async def run_local_analysis(file_path: str, goal: str, wsl_ip: str, language: str) -> dict:
    start_time = time.time()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return {"error": f"File read error: {e}"}

    max_chars = APP_CONFIG.get("limits", {}).get("max_chars_for_local_analysis", 6000)
    if len(content) > max_chars:
        content = content[:max_chars] + "\n\n[...]"

    # Prompt in English for maximum stability and reasoning power
    prompt = f"""
You are a specialized Knowledge Extractor. Your task is to analyze the following text and extract TWO types of information related to the RESEARCH GOAL.

RESEARCH GOAL: "{goal}"
INPUT TEXT LANGUAGE: "{language}"

TASK:
1. Extract a list of key technical entities (names, frameworks, specific ingredients, tools).
2. Extract "Knowledge Chunks": These are high-value text blocks such as:
   - Source code snippets (if any).
   - Detailed recipes or step-by-step procedures.
   - Comprehensive technical explanations or data tables.
   - Historical anecdotes or specific facts.

OUTPUT INSTRUCTIONS:
- Respond ONLY with a valid JSON object.
- Use English for JSON keys.
- Keep the extracted content in its ORIGINAL language.
- Format:
{{
    "entities": ["Entity 1", "Entity 2", ...],
    "knowledge_chunks": [
        {{
            "content": "The full text of the snippet...",
            "type": "code|recipe|technical|anecdote"
        }}
    ]
}}

TEXT TO ANALYZE:
\"\"\"
{content}
\"\"\"

JSON RESPONSE:
"""

    model_name = APP_CONFIG.get("models", {}).get("analyst", "llama3.2:3b")
    ollama_url = f"http://{wsl_ip}:11434/api/generate"
    payload = {
        "model": model_name,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_ctx": 4096,
            "num_predict": 1024 # Increased to allow for longer chunks
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
                            json_str = result_text

                        parsed_json = json.loads(json_str)
                        if not isinstance(parsed_json, dict):
                            return {"error": "JSON is not an object."}
                        return {
                            "entities": parsed_json.get("entities", []),
                            "knowledge_chunks": parsed_json.get("knowledge_chunks", []),
                            "inference_time": time.time() - start_time
                        }
                    except Exception:
                        return {"error": "JSON parsing error."}
                else:
                    return {"error": f"API Error: {response.status}"}
        except Exception as e:
            return {"error": str(e)}

async def analyst_node(state: AgentState) -> AgentState:
    console.print("\n[blue]>>> ANALYST NODE: Extracting Knowledge with Ollama (Llama 3.2)...[/blue]")
    
    session_mock = "sess_001"
    pending_files = get_pending_files(session_mock)
    
    if not pending_files:
        console.print("[yellow]No new files to analyze.[/yellow]")
        return state

    wsl_ip = get_wsl_host_ip()
    new_entities_found = set()
    total_chunks_saved = 0
    
    for url_hash, local_path in pending_files:
        if not local_path:
             mark_file_analyzed(url_hash)
             continue
             
        filename = Path(local_path).name
        
        # Estrai l'URL reale dal frontmatter per log e DB più puliti
        real_url = filename
        try:
            with open(local_path, 'r', encoding='utf-8') as f:
                for _ in range(5): # Controlla solo le prime righe
                    line = f.readline()
                    if line.startswith("url: "):
                        real_url = line.replace("url: ", "").strip()
                        break
        except:
            pass
            
        console.print(f"[cyan]Deep Analysis in progress:[/cyan] {real_url}")
        
        result = await run_local_analysis(local_path, state['goal'], wsl_ip, state['language'])
        
        if "error" in result:
             console.print(f"[red]Error during analysis of {filename}: {result['error']}[/red]")
             continue
             
        entities = result.get("entities", [])
        chunks = result.get("knowledge_chunks", [])
        inf_time = result.get("inference_time", 0.0)
        
        # Save Entities
        valid_entities = [e for e in entities if e and isinstance(e, str) and len(e) < 50]
        if valid_entities:
            save_entities_to_db(session_mock, valid_entities)
            new_entities_found.update(valid_entities)
            
        # Save Knowledge Chunks
        for chunk in chunks:
            content = chunk.get("content")
            c_type = chunk.get("type", "technical")
            if content and len(content) > 20: # Avoid tiny snippets
                save_knowledge_chunk(session_mock, real_url, content, c_type)
                total_chunks_saved += 1
        
        console.print(Panel(
            f"[green]File:[/green] {filename}\n"
            f"[yellow]Entities:[/yellow] {len(valid_entities)}\n"
            f"[cyan]Knowledge Chunks:[/cyan] {len(chunks)}\n"
            f"[magenta]GPU Time:[/magenta] {inf_time:.2f}s",
            title="Extraction Result", border_style="blue"
        ))
            
        mark_file_analyzed(url_hash)

    all_db_entities = get_entities_from_db(session_mock)
    unique_entities_count = len(all_db_entities)
    calculated_saturation = min(unique_entities_count / 50.0, 1.0)
    
    console.print(f"\n[bold blue]Total entities in DB:[/bold blue] {unique_entities_count}")
    console.print(f"[bold cyan]Total knowledge chunks saved:[/bold cyan] {total_chunks_saved}")
    console.print(f"[bold magenta]Saturation Score:[/bold magenta] {calculated_saturation:.2f}")

    is_saturated = False
    if calculated_saturation >= 0.85:
        is_saturated = True

    return {
        **state,
        "entities": list(set(state.get("entities", []) + list(new_entities_found))),
        "saturation_score": calculated_saturation,
        "is_saturated": is_saturated
    }

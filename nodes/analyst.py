import time
import re
import json
import aiohttp
from pathlib import Path
from core.state import AgentState
from core.config import console, APP_CONFIG
from database.db_manager import get_wsl_host_ip, get_pending_files, mark_file_analyzed, save_entities_to_db, get_entities_from_db
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

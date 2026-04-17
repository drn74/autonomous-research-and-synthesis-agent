import time
import re
import json
import aiohttp
import asyncio
from pathlib import Path
from core.state import AgentState
from core.config import console, APP_CONFIG
from core.resource_handler import split_text_into_chunks
from database.db_manager import get_ollama_host, get_ollama_port, get_pending_files, mark_file_analyzed, save_entities_to_db, get_entities_from_db, save_knowledge_chunk
from database.vector_manager import VectorManager
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

async def run_local_analysis(content: str, goal: str, host: str, port: int, language: str, semaphore: asyncio.Semaphore, feedback: str = None) -> dict:
    """Performs extraction on a single text chunk using Ollama with concurrency control and optional feedback."""
    async with semaphore:
        start_time = time.time()
        
        # Sanitize input
        content = content.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
        content = re.sub(r'[ \t]+', ' ', content)
        content = re.sub(r'\n{3,}', '\n\n', content)

        feedback_instruction = f"\nCRITIC FEEDBACK FROM PREVIOUS ATTEMPT: {feedback}\nPlease address this feedback in your current extraction." if feedback else ""

        # Prompt enhanced with feedback
        prompt = f"""
    You are a specialized Knowledge Extractor. Your task is to analyze the following text and extract TWO types of information related to the RESEARCH GOAL.
    {feedback_instruction}

    RESEARCH GOAL: "{goal}"
    INPUT TEXT LANGUAGE: "{language}"

    TASK:
    1. Extract a list of key technical entities (names, frameworks, specific ingredients, tools).
    2. Extract "Knowledge Chunks": These are high-value text blocks such as source code, recipes, or facts.

    OUTPUT INSTRUCTIONS:
    - Respond ONLY with a valid JSON object.
    - Format:
    {{
        "entities": ["Entity 1", "Entity 2", ...],
        "knowledge_chunks": [
            {{
                "content": "The full text...",
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
        ollama_url = f"http://{host}:{port}/api/generate"
        payload = {
            "model": model_name,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.0, "num_ctx": 4096, "num_predict": 4096}
        }

        # Increased timeout for large chunks or busy GPUs
        timeout = aiohttp.ClientTimeout(total=180)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.post(ollama_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        result_text = data.get("response", "").strip()
                        match = re.search(r'\{.*\}', result_text, re.DOTALL)
                        json_str = match.group(0) if match else result_text
                        repaired_json_str = re.sub(r'\\u(?![0-9a-fA-F]{4})', r'\\\\u', json_str)
                        parsed_json = json.loads(repaired_json_str)
                        return {
                            "entities": parsed_json.get("entities", []),
                            "knowledge_chunks": parsed_json.get("knowledge_chunks", []),
                            "inference_time": time.time() - start_time
                        }
                    else:
                        return {"error": f"Ollama HTTP {response.status}"}
            except asyncio.TimeoutError:
                return {"error": "Ollama Request Timeout (180s)"}
            except Exception as e:
                return {"error": str(e)}

async def analyst_node(state: AgentState) -> AgentState:
    retry_count = state.get("retry_count", 0)
    feedback = state.get("critic_feedback")
    
    label = f"ANALYST NODE (Attempt {retry_count + 1})"
    console.print(f"\n[blue]>>> {label}: Multi-chunk analysis with Ollama...[/blue]")
    
    session_id = state["session_id"]
    pending_files = get_pending_files(session_id)
    
    if not pending_files:
        console.print("[yellow]No files pending analysis.[/yellow]")
        return state

    ollama_host = get_ollama_host()
    ollama_port = get_ollama_port()
    new_entities_found = set()
    total_chunks_saved = 0
    vector_db = VectorManager()
    gpu_semaphore = asyncio.Semaphore(1)
    chunk_size = APP_CONFIG.get("limits", {}).get("max_chars_for_local_analysis", 5000)
    
    for url_hash, local_path in pending_files:
        if not local_path:
             mark_file_analyzed(url_hash)
             continue
             
        filename = Path(local_path).name
        real_url = filename
        try:
            with open(local_path, 'r', encoding='utf-8') as f:
                full_content = f.read()
                first_lines = full_content.splitlines()[:5]
                for line in first_lines:
                    if line.startswith("url: "):
                        real_url = line.replace("url: ", "").strip()
                        break
        except Exception as e:
            console.print(f"[red]Error reading file {filename}: {e}[/red]")
            mark_file_analyzed(url_hash)
            continue
            
        text_fette = split_text_into_chunks(full_content, chunk_size=chunk_size, chunk_overlap=chunk_size // 10)
        
        file_entities = set()
        file_knowledge_chunks_count = 0
        total_inf_time = 0.0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[cyan]Analyzing {task.fields[filename]}...[/cyan]"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            chunk_task = progress.add_task("chunks", total=len(text_fette), filename=filename[:30])
            
            async def process_chunk_with_progress(fetta, idx):
                res = await run_local_analysis(fetta, state['goal'], ollama_host, ollama_port, state['language'], gpu_semaphore, feedback)
                progress.advance(chunk_task)
                return res

            tasks = [process_chunk_with_progress(fetta, i) for i, fetta in enumerate(text_fette)]
            results = await asyncio.gather(*tasks)
        
        for i, result in enumerate(results):
            if "error" in result:
                 console.print(f"  [red]Error in chunk {i+1} of {filename}: {result['error']}[/red]")
                 continue
                 
            entities = result.get("entities", [])
            chunks = result.get("knowledge_chunks", [])
            total_inf_time += result.get("inference_time", 0.0)
            valid_entities = [e for e in entities if e and isinstance(e, str) and len(e) < 50]
            file_entities.update(valid_entities)
            
            chunks_for_vector_db = []
            metadatas_for_vector_db = []
            for chunk in chunks:
                c_content = chunk.get("content") if isinstance(chunk, dict) else chunk
                c_type = chunk.get("type", "technical") if isinstance(chunk, dict) else "technical"
                if c_content and len(c_content) > 20:
                    save_knowledge_chunk(session_id, real_url, c_content, c_type)
                    chunks_for_vector_db.append(c_content)
                    metadatas_for_vector_db.append({
                        "type": c_type, 
                        "source_url": real_url, 
                        "chunk_index": i, 
                        "retry": retry_count
                    })
                    file_knowledge_chunks_count += 1
            
            if chunks_for_vector_db:
                vector_db.add_chunks(session_id, real_url, chunks_for_vector_db, metadatas_for_vector_db)

        if file_entities:
            save_entities_to_db(session_id, list(file_entities))
            new_entities_found.update(file_entities)
        
        total_chunks_saved += file_knowledge_chunks_count
        console.print(f"[green]✓ {filename} processed.[/green] Entities: {len(file_entities)}, Chunks: {file_knowledge_chunks_count}, Time: {total_inf_time:.2f}s")
        
        if not feedback or retry_count >= 2:
            mark_file_analyzed(url_hash)

    all_db_entities = get_entities_from_db(session_id)
    console.print(f"\n[bold blue]Session Stats:[/bold blue]")
    console.print(f"  - Entities in DB: {len(all_db_entities)}")
    console.print(f"  - New Knowledge Chunks: {total_chunks_saved}")

    return {
        **state,
        "entities": list(set(state.get("entities", []) + list(new_entities_found))),
        "retry_count": retry_count,
        "critic_feedback": feedback
    }

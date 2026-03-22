from core.state import AgentState, PlannerOutput
from core.config import console, APP_CONFIG
from core.llm import get_gemini_model
from database.db_manager import get_entities_from_db, save_entities_to_db
from rich.panel import Panel

async def planner_node(state: AgentState) -> AgentState:
    console.print(Panel(f"[bold cyan]Planning in progress...[/bold cyan]\nLanguage: {state['language'].upper()}\nTopic: {state['topic']}", border_style="cyan"))
    
    session_mock = "sess_001"
    db_entities = get_entities_from_db(session_mock)
    all_entities = list(set(state.get("entities", []) + db_entities))

    llm = get_gemini_model(purpose="planner", temperature=0.2)
    
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

    console.print(f"[dim]Invoking {model_name} (Planner)...[/dim]")
    
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
    max_iter = APP_CONFIG.get("max_iterations", 3)
    sat_thresh = APP_CONFIG.get("saturation_threshold", 0.85)
    
    if result.saturation_estimate >= sat_thresh or new_iteration > max_iter: 
        is_saturated = True
        console.print(f"[bold red]WARNING: Saturation reached (>={sat_thresh}) or Iteration limit exceeded (>{max_iter})![/bold red]")

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

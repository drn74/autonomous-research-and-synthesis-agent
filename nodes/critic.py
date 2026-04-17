import json
import re
from core.state import AgentState
from core.config import console, APP_CONFIG
from core.llm import get_gemini_model
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

class CriticEvaluation(BaseModel):
    is_quality_sufficient: bool = Field(description="True if the extraction is technical and relevant, False if it needs improvement.")
    feedback: str = Field(description="Specific instructions for the Analyst to improve the next extraction.")
    cleaned_entities: list[str] = Field(description="The filtered list of highly relevant entities.")

async def critic_node(state: AgentState) -> AgentState:
    """
    Acts as a quality gate for the Analyst's output.
    Uses Gemini 2.5 Flash to validate and potentially trigger a retry.
    """
    console.print("\n[magenta]>>> CRITIC NODE: Deep Quality Validation with Gemini...[/magenta]")
    
    entities = state.get("entities", [])
    retry_count = state.get("retry_count", 0)
    
    if not entities:
        console.print("[yellow]Critic: No entities found to validate. Triggering retry loop if possible.[/yellow]")
        state["critic_feedback"] = "The last analysis yielded no entities. Please try to be more granular and extract technical concepts, code, or specific facts."
        state["retry_count"] = retry_count + 1
        return state

    llm = get_gemini_model(purpose="critic", temperature=0.1)
    # Give the model structured output capability
    structured_llm = llm.with_structured_output(CriticEvaluation)
    
    # Sample the last entities and a summary of the goal
    sample_entities = entities[-30:]
    
    prompt = f"""
    Act as a Technical Quality Auditor. Your goal is to evaluate if the information extracted by the Analyst is sufficient and relevant.

    RESEARCH GOAL: "{state['goal']}"
    EXTRACTED ENTITIES (Sample): {sample_entities}
    CURRENT RETRY COUNT: {retry_count}

    TASK:
    1. Assess if the entities are specific enough or too generic (e.g., 'data' is generic, 'PostgreSQL index' is specific).
    2. If the quality is low OR if the list is very short for a complex goal, set is_quality_sufficient to False.
    3. Provide specific 'feedback' on what to look for (e.g., "Focus more on the implementation details of X").
    4. Provide a 'cleaned_entities' list removing noise.

    If is_quality_sufficient is False, the Analyst will RE-PROCESS the files with your feedback.
    Be strict: we want high-quality technical data.
    """

    try:
        eval_result = await structured_llm.ainvoke([HumanMessage(content=prompt)])
        
        # Update entities with the cleaned version
        old_entities = state.get("entities", [])[:-30]
        state["entities"] = list(set(old_entities + eval_result.cleaned_entities))
        
        if not eval_result.is_quality_sufficient and retry_count < 2:
            console.print(f"[bold red]Critic: Quality insufficient![/bold red] Feedback: {eval_result.feedback}")
            state["critic_feedback"] = eval_result.feedback
            state["retry_count"] = retry_count + 1
        else:
            if retry_count > 0:
                console.print("[bold green]Critic: Quality improved, proceeding.[/bold green]")
            else:
                console.print("[bold green]Critic: Quality verified.[/bold green]")
            state["critic_feedback"] = None # Clear feedback to exit loop
            
    except Exception as e:
        console.print(f"[red]Critic Error: {e}. Proceeding without retry.[/red]")
        state["critic_feedback"] = None

    return state

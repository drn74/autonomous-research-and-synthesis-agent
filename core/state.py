from typing import List, TypedDict, Optional
from pydantic import BaseModel, Field

class AgentState(TypedDict):
    topic: str
    goal: str
    language: str
    queries: List[str]
    entities: List[str]
    iteration: int
    saturation_score: float
    notes_path: Optional[str]
    plan: Optional[str]
    is_saturated: bool

class PlannerOutput(BaseModel):
    plan_outline: str = Field(description="A textual draft of the work plan or chapters of the final document.")
    new_queries: List[str] = Field(description="List of 3-5 new specific search queries to expand the topic.")
    new_entities_to_track: List[str] = Field(description="Key entities (people, concepts, technologies) just identified to track.")
    saturation_estimate: float = Field(description="A score from 0.0 to 1.0 indicating how much the current entities cover the Goal. 1.0 = Topic completely covered.")

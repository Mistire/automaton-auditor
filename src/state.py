import operator
from typing import Annotated, Dict, List, Literal, Optional, Any
from typing_extensions import TypedDict
from pydantic import BaseModel, Field


# --- Detective Layer: Forensic Evidence ---

class Evidence(BaseModel):
    """A single piece of forensic evidence collected by a Detective."""
    goal: str = Field(description="What was being investigated")
    found: bool = Field(description="Whether the artifact or pattern was found")
    content: Optional[str] = Field(default=None, description="Extracted content, code snippet, or text excerpt")
    location: str = Field(description="File path, commit hash, or PDF section/page")
    rationale: str = Field(description="Brief explanation of the finding and its relevance")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the accuracy of this specific finding")


# --- Judicial Layer: Perspectives (Prosecutor, Defense, Tech Lead) ---

class JudicialOpinion(BaseModel):
    """An opinion from a single judge on a single rubric criterion."""
    judge: Literal["Prosecutor", "Defense", "TechLead"]
    criterion_id: str
    score: int = Field(description="Score matching the rubric levels defined in the constitution")
    argument: str = Field(description="Detailed philosophical and technical argument for this score")
    cited_evidence: List[str] = Field(description="List of specific evidence goals/locations referenced in this argument")


# --- Supreme Court: Final Synthesis ---

class CriterionResult(BaseModel):
    """The final synthesized result for a single rubric dimension."""
    dimension_id: str
    dimension_name: str
    final_score: int
    judge_opinions: List[JudicialOpinion]
    dissent_summary: Optional[str] = Field(
        default=None, 
        description="Explanation of conflicting views if judge scores varied significantly"
    )
    remediation: str = Field(
        description="Actionable, file-level instructions to reach the next score level"
    )


class AuditReport(BaseModel):
    """The complete audit report output model."""
    repo_url: str
    executive_summary: str
    overall_score: float
    criteria: List[CriterionResult]
    remediation_plan: str
    timestamp: str


# --- LangGraph Orchestration State ---

class AgentState(BaseModel):
    """
    The shared state flowing through the LangGraph StateGraph.
    Upgraded to Pydantic BaseModel for 'Architectural Soundness'.
    """
    repo_url: str
    pdf_path: Optional[str] = None
    local_repo_path: Optional[str] = None
    
    # Configuration
    rubric_dimensions: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Collected Evidence (Parallel Detectives)
    evidences: Annotated[Dict[str, List[Evidence]], operator.ior] = Field(default_factory=dict)
    
    # Judicial Opinions (Parallel Judges)
    opinions: Annotated[List[JudicialOpinion], operator.add] = Field(default_factory=list)
    
    # Final Result
    final_report: Optional[AuditReport] = None
    
    # Error management
    errors: Annotated[List[str], operator.add] = Field(default_factory=list)

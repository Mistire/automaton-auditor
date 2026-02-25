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
    score: int = Field(ge=1, le=5, description="Score matching the levels 1, 3, or 5 in the rubric")
    argument: str = Field(description="Detailed philosophical and technical argument for this score")
    cited_evidence: List[str] = Field(description="List of specific evidence goals/locations referenced in this argument")


# --- Supreme Court: Final Synthesis ---

class CriterionResult(BaseModel):
    """The final synthesized result for a single rubric dimension."""
    dimension_id: str
    dimension_name: str
    final_score: int = Field(ge=1, le=5)
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

class AgentState(TypedDict):
    """The shared state flowing through the LangGraph StateGraph."""
    repo_url: str
    pdf_path: str
    
    # Configuration
    rubric_dimensions: List[Dict[str, Any]]
    
    # Collected Evidence (Parallel Detectives)
    # operator.ior merges dictionaries (detective_name -> list of Evidence)
    evidences: Annotated[Dict[str, List[Evidence]], operator.ior]
    
    # Judicial Opinions (Parallel Judges)
    # operator.add accumulates opinions in a single list
    opinions: Annotated[List[JudicialOpinion], operator.add]
    
    # Final Result
    final_report: Optional[AuditReport]
    
    # Error management
    errors: Annotated[List[str], operator.add]

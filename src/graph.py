from langgraph.graph import StateGraph, START, END
from src.state import AgentState
from src.nodes.detectives import (
    repo_investigator,
    doc_analyst,
    vision_inspector,
    evidence_aggregator
)
from src.nodes.judges import (
    prosecutor_node,
    defense_node,
    tech_lead_node
)
from src.nodes.justice import chief_justice_node


def should_aggregate_or_abort(state: AgentState) -> str:
    """
    Conditional edge after fan-in: checks if we have enough evidence to proceed,
    or if critical errors mean we should abort early.
    """
    errors = state.get("errors", [])
    evidences = state.get("evidences", {})

    # If ALL detectives failed (no evidence at all), abort
    if not evidences and errors:
        return "abort"

    # If we have at least some evidence, proceed to aggregation
    return "aggregate"


def after_aggregation(state: AgentState) -> str:
    """
    Conditional edge after aggregation: route to judges or end.
    """
    evidences = state.get("evidences", {})
    
    # Count total evidence items (summing all lists in the dict)
    total_evidence = sum(len(v) for v in evidences.values())

    # If we have very little evidence, it's hard for judges to work
    if total_evidence < 1:
        return "abort"

    # Normal path: enough evidence collected to proceed to the Digital Courtroom
    return "sufficient_evidence"


def abort_node(state: AgentState) -> dict:
    """Terminal node when detectives fail or evidence is missing."""
    return {"errors": ["ABORT: Insufficient evidence collected to proceed to Judicial review."]}


# ── Build the graph ──────────────────────────────────────────────

builder = StateGraph(AgentState)

# Register nodes
builder.add_node("repo_investigator", repo_investigator)
builder.add_node("doc_analyst", doc_analyst)
builder.add_node("vision_inspector", vision_inspector)
builder.add_node("evidence_aggregator", evidence_aggregator)
builder.add_node("abort", abort_node)

# Phase 2 Nodes
builder.add_node("prosecutor", prosecutor_node)
builder.add_node("defense", defense_node)
builder.add_node("tech_lead", tech_lead_node)
builder.add_node("chief_justice", chief_justice_node)

# ── Fan-out Phase 1: START → 3 detectives in parallel ────────────
builder.add_edge(START, "repo_investigator")
builder.add_edge(START, "doc_analyst")
builder.add_edge(START, "vision_inspector")

# ── Fan-in Phase 1: all detectives → conditional check ───────────
builder.add_conditional_edges(
    "repo_investigator",
    should_aggregate_or_abort,
    {"aggregate": "evidence_aggregator", "abort": "abort"}
)
builder.add_conditional_edges(
    "doc_analyst",
    should_aggregate_or_abort,
    {"aggregate": "evidence_aggregator", "abort": "abort"}
)
builder.add_conditional_edges(
    "vision_inspector",
    should_aggregate_or_abort,
    {"aggregate": "evidence_aggregator", "abort": "abort"}
)

# ── Fan-out Phase 2: Aggregator → Parallel Judges ────────────────
builder.add_node("router_to_judges", lambda x: x) # Pass-through node for fan-out

builder.add_conditional_edges(
    "evidence_aggregator",
    after_aggregation,
    {
        "sufficient_evidence": "router_to_judges",
        "abort": "abort"
    }
)

# Branch out from the router
builder.add_edge("router_to_judges", "prosecutor")
builder.add_edge("router_to_judges", "defense")
builder.add_edge("router_to_judges", "tech_lead")

# ── Fan-in Phase 2: Parallel Judges → Chief Justice ──────────────
builder.add_edge("prosecutor", "chief_justice")
builder.add_edge("defense", "chief_justice")
builder.add_edge("tech_lead", "chief_justice")

# ── Final Verdict ────────────────────────────────────────────────
builder.add_edge("chief_justice", END)
builder.add_edge("abort", END)

# Compile
graph = builder.compile()

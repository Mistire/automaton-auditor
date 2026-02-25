from langgraph.graph import StateGraph, START, END
from src.state import AgentState
from src.nodes.detectives import (
    repo_investigator,
    doc_analyst,
    vision_inspector,
    evidence_aggregator
)


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
    Conditional edge after aggregation: route to judges (future) or end.
    Checks evidence quality to decide if judicial review is warranted.
    """
    evidences = state.get("evidences", {})
    errors = state.get("errors", [])

    # Count total evidence items
    total_evidence = sum(len(v) for v in evidences.values())

    # If we have very little evidence, flag it but still end
    if total_evidence < 2:
        return "insufficient_evidence"

    # Normal path: enough evidence collected
    return "sufficient_evidence"


def abort_node(state: AgentState) -> dict:
    """Terminal node when all detectives fail."""
    return {"errors": ["ABORT: All detective nodes failed. No evidence was collected. "
                       "Check repo URL and PDF path."]}


# ── Build the graph ──────────────────────────────────────────────

builder = StateGraph(AgentState)

# Register nodes
builder.add_node("repo_investigator", repo_investigator)
builder.add_node("doc_analyst", doc_analyst)
builder.add_node("vision_inspector", vision_inspector)
builder.add_node("evidence_aggregator", evidence_aggregator)
builder.add_node("abort", abort_node)

# ── Fan-out: START → 3 detectives in parallel ────────────────────
builder.add_edge(START, "repo_investigator")
builder.add_edge(START, "doc_analyst")
builder.add_edge(START, "vision_inspector")

# ── Fan-in: all detectives → conditional check ───────────────────
# LangGraph waits for all incoming edges before evaluating the condition.
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

# ── After aggregation: conditional routing ────────────────────────
builder.add_conditional_edges(
    "evidence_aggregator",
    after_aggregation,
    {
        "sufficient_evidence": END,       # In final: route to judges
        "insufficient_evidence": END,     # End with warning
    }
)

builder.add_edge("abort", END)

# Compile
graph = builder.compile()

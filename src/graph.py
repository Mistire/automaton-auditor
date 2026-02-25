from langgraph.graph import StateGraph, START, END
from src.state import AgentState
from src.nodes.detectives import (
    repo_investigator, 
    doc_analyst, 
    vision_inspector, 
    evidence_aggregator
)


# Define the graph
builder = StateGraph(AgentState)

# Add nodes
builder.add_node("repo_investigator", repo_investigator)
builder.add_node("doc_analyst", doc_analyst)
builder.add_node("vision_inspector", vision_inspector)
builder.add_node("evidence_aggregator", evidence_aggregator)

# 1. Start -> Parallel Detectives (Fan-out)
builder.add_edge(START, "repo_investigator")
builder.add_edge(START, "doc_analyst")
builder.add_edge(START, "vision_inspector")

# 2. Detectives -> Aggregator (Fan-in)
# LangGraph handles the synchronization automatically when multiple edges 
# point to the same node and the state has reducers for the relevant keys.
builder.add_edge("repo_investigator", "evidence_aggregator")
builder.add_edge("doc_analyst", "evidence_aggregator")
builder.add_edge("vision_inspector", "evidence_aggregator")

# 3. Aggregator -> END (for Interim)
# In final, this will route to Judges.
builder.add_edge("evidence_aggregator", END)

# Compile
graph = builder.compile()

from typing import Dict, List
from src.state import AgentState, Evidence
from src.tools import repo_tools, doc_tools


def repo_investigator(state: AgentState) -> Dict:
    """
    Detective Node: Analyzes the GitHub repository structure and history.
    """
    repo_url = state.get("repo_url")
    if not repo_url:
        return {"errors": ["No repository URL provided."]}
    
    evidences = []
    repo_path = None
    try:
        # 1. Clone
        repo_path = repo_tools.clone_repo(repo_url)
        
        # 2. Forensic Protocols
        evidences.extend(repo_tools.extract_git_history(repo_path))
        evidences.extend(repo_tools.analyze_state_structure(repo_path))
        evidences.extend(repo_tools.analyze_graph_orchestration(repo_path))
        evidences.extend(repo_tools.analyze_safe_tooling(repo_path))
        evidences.extend(repo_tools.analyze_structured_output(repo_path))
        
    except Exception as e:
        return {"errors": [f"RepoInvestigator failed: {str(e)}"]}
    
    return {"evidences": {"repo": evidences}}


def doc_analyst(state: AgentState) -> Dict:
    """
    Detective Node: Analyzes the architectural PDF report.
    """
    pdf_path = state.get("pdf_path")
    repo_evidences = state.get("evidences", {}).get("repo", [])
    
    if not pdf_path:
        # Graceful skip if no PDF provided
        return {"evidences": {"doc": [Evidence(
            goal="pdf_report_existence",
            found=False,
            location="N/A",
            rationale="No PDF report path provided in input.",
            confidence=1.0
        )]}}
    
    evidences = []
    try:
        # 1. Ingest
        chunks = doc_tools.ingest_pdf(pdf_path)
        full_text = "\n".join([c["text"] for c in chunks])
        
        # 2. Extract paths
        report_paths = doc_tools.extract_file_paths(full_text)
        
        # 3. Cross-reference (requires cloned repo path from state or internal knowledge)
        # Note: In a real fan-out, doc_analyst might not have the repo_path yet 
        # unless it's stored in state by repo_investigator or handled in aggregator.
        # For interim, we'll assume aggregator handles the cross-ref or we store path.
        
        # 4. Concept Depth protocols
        concepts = ["Dialectical Synthesis", "Fan-In / Fan-Out", "Metacognition", "State Synchronization"]
        for concept in concepts:
            is_deep, excerpt = doc_tools.check_concept_depth(full_text, concept)
            evidences.append(Evidence(
                goal=f"theoretical_depth_{concept.lower().replace(' ', '_')}",
                found=is_deep,
                content=excerpt[:200],
                location="PDF Report",
                rationale=f"Verified conceptual depth for '{concept}'.",
                confidence=0.8
            ))
            
    except Exception as e:
        return {"errors": [f"DocAnalyst failed: {str(e)}"]}
    
    return {"evidences": {"doc": evidences}}


def vision_inspector(state: AgentState) -> Dict:
    """
    Detective Node: Analyzes diagrams in the PDF. (Implementation optional/stub)
    """
    return {"evidences": {"vision": [Evidence(
        goal="swarm_visual",
        found=False,
        location="PDF Images",
        rationale="VisionInspector implementation is a stub for interim.",
        confidence=0.5
    )]}}


def evidence_aggregator(state: AgentState) -> Dict:
    """
    Synchronization Node: Performs cross-dimensional verification 
    (e.g., matching report claims against repo facts).
    """
    repo_evidences = state.get("evidences", {}).get("repo", [])
    doc_evidences = state.get("evidences", {}).get("doc", [])
    
    # Logic to cross-verify goes here...
    # For now, just a pass-through node that ensures state is ready for Judges.
    
    return {"errors": []} # No-op basically, just for fan-in logic

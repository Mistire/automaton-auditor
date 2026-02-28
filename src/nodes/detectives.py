from src.tools.llm_tools import get_llm
from langchain_core.messages import HumanMessage
import base64
import os
from typing import Dict, List
from src.state import AgentState, Evidence
from src.tools import repo_tools, doc_tools


def repo_investigator(state: AgentState) -> Dict:
    """
    Detective Node: Analyzes the repository dynamically based on the rubric.
    Iterates through rubric dimensions and dispatches to specialized tools or fallback.
    """
    repo_url = state.repo_url
    local_path = state.local_repo_path
    dimensions = state.rubric_dimensions
    
    evidences = []
    repo_path = None
    
    # 1. Specialized Dispatch Mapping
    REPOMAPPING = {
        "git_forensic_analysis": repo_tools.extract_git_history,
        "state_management_rigor": repo_tools.analyze_state_structure,
        "graph_orchestration": repo_tools.analyze_graph_orchestration,
        "safe_tool_engineering": repo_tools.analyze_safe_tooling,
        "structured_output_enforcement": repo_tools.analyze_structured_output,
        "judicial_nuance": repo_tools.analyze_judicial_nuance,
        "chief_justice_synthesis": repo_tools.analyze_justice_synthesis,
    }

    try:
        # Clone or use local
        if local_path and os.path.exists(local_path):
            repo_path = local_path
        else:
            if not repo_url:
                return {"errors": ["RepoInvestigator: No source provided."]}
            print(f"🌐 Cloning: {repo_url}")
            repo_path = repo_tools.clone_repo(repo_url)

        # 2. Dynamic Execution Loop
        for dim in dimensions:
            if dim.get("target_artifact") != "github_repo":
                continue
                
            dim_id = dim["id"]
            print(f"🔍 Investigating: {dim_id}")
            
            if dim_id in REPOMAPPING:
                # Dispatch to specialized logic
                evidences.extend(REPOMAPPING[dim_id](repo_path))
            else:
                # ADAPTIVE FALLBACK: Use crawler with keywords from instruction
                instr = dim.get("forensic_instruction", "")
                # Basic keyword extraction (split by space, filter small words)
                keywords = [w.strip("',.") for w in instr.split() if len(w) > 4][:5]
                print(f"  ⚠️ No specialized tool for {dim_id}. Falling back to keyword crawl: {keywords}")
                evidence_results = repo_tools.file_content_crawler(repo_path, keywords)
                evidences.extend(evidence_results)
            
            # Print feedback for each evidence found
            for e in evidences[-1:] if evidences else []:
                 status = "✅" if e.found else "❌"
                 print(f"  {status} Evidence: {e.goal} | Rationale: {e.rationale}")

    except Exception as e:
        return {"errors": [f"RepoInvestigator failed: {str(e)}"]}

    # PDF Discovery (Shared with other detectives running in parallel)
    pdf_path = None
    if repo_path:
        report_dir = os.path.join(repo_path, "reports")
        if os.path.exists(report_dir):
            pdfs = [f for f in os.listdir(report_dir) if f.endswith(".pdf")]
            if pdfs: pdf_path = os.path.join(report_dir, pdfs[0])

    return {"evidences": {"repo": evidences}, "local_repo_path": repo_path, "pdf_path": pdf_path}



def doc_analyst(state: AgentState) -> Dict:
    """
    Detective Node: Analyzes the architectural PDF report dynamically.
    Refactored to be instruction-aware based on the rubric.
    """
    pdf_path = state.pdf_path
    repo_path = state.local_repo_path
    dimensions = state.rubric_dimensions

    # PDF is now discovered by repo_investigator and shared via state

    if not pdf_path:
        return {"evidences": {"doc": [Evidence(goal="pdf_report", found=False, location="N/A", rationale="No PDF found.", confidence=1.0)]}}

    evidences = []
    try:
        chunks = doc_tools.ingest_pdf(pdf_path)
        full_text = "\n".join([c["text"] for c in chunks])

        for dim in dimensions:
            if dim.get("target_artifact") != "pdf_report":
                continue
            
            dim_id = dim["id"]
            instr = dim.get("forensic_instruction", "")
            
            if dim_id == "report_accuracy":
                raw_paths = doc_tools.extract_file_paths(full_text)
                if repo_path:
                    verified, hallucinated = doc_tools.cross_reference_paths(raw_paths, repo_path)
                    evidences.append(Evidence(
                        goal="report_accuracy", found=len(verified) > 0,
                        content=f"Verified: {verified}\nHallucinated: {hallucinated}",
                        location="PDF Report", rationale=f"Cross-referenced {len(raw_paths)} paths.", confidence=1.0
                    ))
                    if hallucinated:
                        evidences.append(Evidence(goal="path_hallucinations_detected", found=True, content=", ".join(hallucinated), location="PDF Report", rationale="Hallucinated paths detected.", confidence=1.0))
            
            elif dim_id == "theoretical_depth":
                concepts = ["Dialectical Synthesis", "Fan-In", "Metacognition", "State Synchronization"]
                for concept in concepts:
                    is_deep, excerpt = doc_tools.check_concept_depth(full_text, concept)
                    evidences.append(Evidence(goal=f"depth_{concept.lower()}", found=is_deep, content=excerpt[:200], location="PDF Report", rationale=f"Depth check for {concept}", confidence=0.8))
            
            else:
                # ADAPTIVE FALLBACK: Keyword search in PDF
                keywords = [w.strip("',.") for w in instr.split() if len(w) > 4][:3]
                found = any(k.lower() in full_text.lower() for k in keywords)
                snippet = ""
                if found:
                    k = next(k for k in keywords if k.lower() in full_text.lower())
                    idx = full_text.lower().find(k.lower())
                    snippet = full_text[max(0, idx-100):idx+200]
                
                evidences.append(Evidence(
                    goal=dim_id, found=found, content=snippet, location="PDF text search",
                    rationale=f"Adaptive PDF check for keywords: {keywords}", confidence=0.7
                ))
            
            # Print feedback for latest result
            e = evidences[-1]
            status = "✅" if e.found else "❌"
            print(f"  {status} Evidence: {e.goal} | Rationale: {e.rationale}")

    except Exception as e:
        return {"errors": [f"DocAnalyst failed: {str(e)}"]}

    return {"evidences": {"doc": evidences}}


def vision_inspector(state: AgentState) -> Dict:
    """
    Detective Node: Analyzes PDF images dynamically based on the rubric.
    """
    pdf_path = state.pdf_path
    dimensions = state.rubric_dimensions
    
    if not pdf_path:
        return {"evidences": {"vision": [Evidence(goal="pdf_vision", found=False, location="N/A", rationale="No PDF for vision.", confidence=1.0)]}}

    evidences = []
    try:
        image_paths = doc_tools.extract_images_from_pdf(pdf_path)
        if not image_paths:
            return {"evidences": {"vision": [Evidence(goal="pdf_images", found=False, location="PDF", rationale="No images found.", confidence=0.9)]}}

        vision_llm = get_llm(model_id="google/gemini-2.0-flash:free")
        target_images = image_paths[:2] # Limit to 2 images for efficiency

        for dim in dimensions:
            if dim.get("target_artifact") != "pdf_images":
                continue
            
            dim_id = dim["id"]
            instr = dim.get("forensic_instruction", "")
            
            for i, img_path in enumerate(target_images):
                with open(img_path, "rb") as f:
                    img_data = base64.b64encode(f.read()).decode("utf-8")
                
                message = HumanMessage(content=[
                    {"type": "text", "text": f"Evaluate this image for the rubric dimension: {dim_id}\nInstruction: {instr}\nRespond in JSON with 'found' (bool), 'description' (str), and 'parallel_patterns' (str)."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}}
                ])
                
                try:
                    res = vision_llm.invoke([message])
                    evidences.append(Evidence(
                        goal=f"{dim_id}_img_{i}", found=True, content=res.content[:300],
                        location=f"Image {i+1}", rationale=f"Multimodal analysis of {dim_id}", confidence=0.8
                    ))
                except Exception as ve:
                    print(f"Vision error for {dim_id}: {ve}")
                    continue

    except Exception as e:
        return {"errors": [f"VisionInspector failed: {str(e)}"]}

    return {"evidences": {"vision": evidences}}


def evidence_aggregator(state: AgentState) -> Dict:
    """
    Synchronization Node: Consolidates evidence dynamically.
    """
    evidences = state.evidences
    aggregation_evidence = []

    # 1. Completeness Audit
    expected_sources = ["repo", "doc", "vision"]
    missing_sources = [s for s in expected_sources if s not in evidences]
    present_sources = [s for s in expected_sources if s in evidences]

    aggregation_evidence.append(Evidence(
        goal="evidence_completeness", found=len(missing_sources) == 0,
        content=f"Present: {present_sources}, Missing: {missing_sources}",
        location="Aggregator", rationale=f"Audited {len(present_sources)} branches.", confidence=1.0
    ))

    # 2. Dynamic Summary
    all_evidence_items = []
    for source, items in evidences.items():
        all_evidence_items.extend(items)

    if all_evidence_items:
        avg_confidence = sum(e.confidence for e in all_evidence_items) / len(all_evidence_items)
        found_count = sum(1 for e in all_evidence_items if e.found)
        total_count = len(all_evidence_items)

        aggregation_evidence.append(Evidence(
            goal="quality_audit", found=avg_confidence > 0.6,
            content=f"Found {found_count} of {total_count} forensic markers.",
            location="Aggregator", rationale=f"Normalized confidence: {avg_confidence:.2f}",
            confidence=avg_confidence
        ))

    print("\n📦 Evidence Aggregator: Consolidating Detective findings...")
    for e in aggregation_evidence:
        status = "✅" if e.found else "⚠️"
        print(f"  {status} {e.goal}: {e.rationale}")

    return {"evidences": {"aggregation": aggregation_evidence}}

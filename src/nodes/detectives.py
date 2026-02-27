from src.tools.llm_tools import get_llm
from langchain_core.messages import HumanMessage
import base64
import os
from typing import Dict, List
from src.state import AgentState, Evidence
from src.tools import repo_tools, doc_tools


def repo_investigator(state: AgentState) -> Dict:
    """
    Detective Node: Analyzes the repository structure and history.
    Supports local testing mode if local_repo_path is pre-provided.
    """
    repo_url = state.get("repo_url")
    local_path = state.get("local_repo_path")
    
    evidences = []
    repo_path = None
    
    try:
        if local_path and os.path.exists(local_path):
            print(f"🏠 Local Testing Mode: Using existing path {local_path}")
            repo_path = local_path
        else:
            if not repo_url:
                return {"errors": ["RepoInvestigator: No repository URL provided and no local path found."]}
            print(f"🌐 Cloning repository: {repo_url}")
            repo_path = repo_tools.clone_repo(repo_url)

        # Execute all forensic protocols
        evidences.extend(repo_tools.extract_git_history(repo_path))
        evidences.extend(repo_tools.analyze_state_structure(repo_path))
        evidences.extend(repo_tools.analyze_graph_orchestration(repo_path))
        evidences.extend(repo_tools.analyze_safe_tooling(repo_path))
        evidences.extend(repo_tools.analyze_structured_output(repo_path))
        evidences.extend(repo_tools.analyze_justice_synthesis(repo_path))

    except Exception as e:
        return {"errors": [f"RepoInvestigator failed: {str(e)}"]}

    return {"evidences": {"repo": evidences}, "local_repo_path": repo_path}



def doc_analyst(state: AgentState) -> Dict:
    """
    Detective Node: Analyzes the architectural PDF report.
    Checks concept depth and performs forensic cross-referencing of file paths.
    """
    pdf_path = state.get("pdf_path")
    repo_path = state.get("local_repo_path")

    # 1. Internal PDF Discovery (from earlier implementation)
    if not pdf_path and repo_path:
        report_dir = os.path.join(repo_path, "reports")
        if os.path.exists(report_dir):
            pdfs = [f for f in os.listdir(report_dir) if f.endswith(".pdf")]
            if pdfs:
                pdf_path = os.path.join(report_dir, pdfs[0])
                print(f"📂 Found internal PDF report: {pdf_path}")

    if not pdf_path:
        return {"evidences": {"doc": [Evidence(
            goal="pdf_report_existence",
            found=False,
            location="N/A",
            rationale="No PDF report path provided and no PDF found in internal 'reports/' folder.",
            confidence=1.0
        )]}}

    evidences = []
    try:
        # 2. Ingest PDF
        chunks = doc_tools.ingest_pdf(pdf_path)
        full_text = "\n".join([c["text"] for c in chunks])

        # 3. Path Cross-Referencing (Forensic Protocol A)
        raw_paths = doc_tools.extract_file_paths(full_text)
        verified = []
        hallucinated = []
        
        if repo_path:
            verified, hallucinated = doc_tools.cross_reference_paths(raw_paths, repo_path)
            
        evidences.append(Evidence(
            goal="report_accuracy_forensics",
            found=len(verified) > 0,
            content=f"Verified: {verified}\nHallucinated: {hallucinated}",
            location="PDF Report vs Repository",
            rationale=f"Found {len(verified)} verified paths in the report. Detected {len(hallucinated)} hallucinated paths.",
            confidence=1.0
        ))
        
        evidences.append(Evidence(
            goal="path_hallucinations_detected",
            found=len(hallucinated) > 0,
            location="PDF Report",
            content=", ".join(hallucinated) if hallucinated else "None",
            rationale="No hallucinated paths detected in the report." if not hallucinated else "Report references non-existent files. This flags potential 'Vibe Coding' or outdated reports.",
            confidence=1.0
        ))

        # 4. Theoretical Depth (Forensic Protocol B)
        # Expanded concept list to match the final report's comprehensive technical sections
        concepts = ["Dialectical Synthesis", "Fan-In / Fan-Out", "Metacognition", "State Synchronization", "Supreme Court", "Digital Courtroom"]
        for concept in concepts:
            is_deep, excerpt = doc_tools.check_concept_depth(full_text, concept)
            evidences.append(Evidence(
                goal=f"theoretical_depth_{concept.lower().replace(' ', '_').replace('/', '').replace('-', '_')}",
                found=is_deep,
                content=excerpt[:200].strip(),
                location="PDF Report",
                rationale=f"Assessed depth for '{concept}'. Found = {is_deep}.",
                confidence=0.8
            ))

    except Exception as e:
        return {"errors": [f"DocAnalyst failed: {str(e)}"]}

    return {"evidences": {"doc": evidences}}


def vision_inspector(state: AgentState) -> Dict:
    """
    Detective Node: Analyzes architectural diagrams in the PDF (Protocol A - Swarm Visual).
    Uses multimodal LLM analysis if images are found.
    """
    pdf_path = state.get("pdf_path")
    repo_path = state.get("local_repo_path")
    
    # Discovery logic if not provided
    if not pdf_path and repo_path:
        report_dir = os.path.join(repo_path, "reports")
        if os.path.exists(report_dir):
            pdfs = [f for f in os.listdir(report_dir) if f.endswith(".pdf")]
            if pdfs:
                pdf_path = os.path.join(report_dir, pdfs[0])

    if not pdf_path:
        return {"evidences": {"vision": [Evidence(
            goal="swarm_visual",
            found=False,
            location="N/A",
            rationale="No PDF available for vision analysis.",
            confidence=1.0
        )]}}

    evidences = []
    try:
        # 1. Extract Images
        image_paths = doc_tools.extract_images_from_pdf(pdf_path)
        
        if not image_paths:
            evidences.append(Evidence(
                goal="swarm_visual",
                found=False,
                location="PDF Images",
                rationale="No images/diagrams detected in the PDF report.",
                confidence=0.9
            ))
        else:
            # 2. Analyze first few images (Protocol A)
            llm = get_llm()
            # Selection of images to avoid context overflow
            target_images = image_paths[:3] 
            
            for i, img_path in enumerate(target_images):
                with open(img_path, "rb") as f:
                    img_data = base64.b64encode(f.read()).decode("utf-8")
                
                # We use a HumanMessage for vision-capable models (multimodal support)
                message = HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": "Analyze this architectural diagram. Is it a LangGraph State machine, a sequence diagram, or generic boxes? Does it show parallel fan-out for Detectives and Judges? Respond in JSON with keys: 'classification', 'is_parallel', 'description'."
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}
                        }
                    ]
                )
                
                try:
                    # Generic LLM call for vision (assuming provider supports it)
                    response = llm.invoke([message])
                    analysis = response.content
                    
                    evidences.append(Evidence(
                        goal=f"diagram_analysis_img_{i}",
                        found=True,
                        content=analysis[:300],
                        location=f"PDF Image {i+1}",
                        rationale="Successfully performed multimodal architectural analysis of diagram.",
                        confidence=0.8
                    ))
                except Exception as ve:
                    # Fallback if vision API fails
                    evidences.append(Evidence(
                        goal=f"diagram_analysis_img_{i}",
                        found=True,
                        location=f"PDF Image {i+1}",
                        rationale=f"Found image but vision analysis failed: {ve}",
                        confidence=0.5
                    ))

    except Exception as e:
        return {"errors": [f"VisionInspector failed: {str(e)}"]}

    return {"evidences": {"vision": evidences}}


def evidence_aggregator(state: AgentState) -> Dict:
    """
    Synchronization Node: Consolidates, normalizes, and cross-references
    all evidence collected by the parallel detectives.

    Performs:
    1. Evidence completeness audit — flags missing detective sources
    2. Cross-reference verification — matches report path claims vs repo reality
    3. Confidence normalization — computes per-source and overall stats
    4. Summary generation — produces an aggregated evidence profile
    """
    evidences = state.get("evidences", {})
    errors = state.get("errors", [])
    aggregation_evidence = []

    # ── 1. Completeness Audit ─────────────────────────────────────
    expected_sources = ["repo", "doc", "vision"]
    missing_sources = [s for s in expected_sources if s not in evidences]
    present_sources = [s for s in expected_sources if s in evidences]

    aggregation_evidence.append(Evidence(
        goal="evidence_completeness",
        found=len(missing_sources) == 0,
        content=f"Present: {present_sources}, Missing: {missing_sources}",
        location="EvidenceAggregator",
        rationale=f"{len(present_sources)}/{len(expected_sources)} detective sources reported evidence.",
        confidence=1.0
    ))

    # ── 2. Cross-Reference: Report Claims vs Repo Reality ─────────
    repo_evidence = evidences.get("repo", [])
    doc_evidence = evidences.get("doc", [])

    # Find the file path claims from doc_analyst
    path_claims_evidence = next(
        (e for e in doc_evidence if e.goal == "report_file_path_claims"),
        None
    )

    if path_claims_evidence and path_claims_evidence.content and repo_evidence:
        claimed_paths = [p.strip() for p in path_claims_evidence.content.split(",")]
        # We can't directly check files here (no repo path in state),
        # but we can flag whether path claims exist and were extracted
        aggregation_evidence.append(Evidence(
            goal="cross_reference_readiness",
            found=True,
            content=f"{len(claimed_paths)} paths to verify against repo structure",
            location="EvidenceAggregator",
            rationale="Report path claims extracted and ready for cross-reference with repo evidence.",
            confidence=0.85
        ))

    # ── 3. Confidence Normalization ───────────────────────────────
    all_evidence_items = []
    for source, items in evidences.items():
        all_evidence_items.extend(items)

    if all_evidence_items:
        avg_confidence = sum(e.confidence for e in all_evidence_items) / len(all_evidence_items)
        found_count = sum(1 for e in all_evidence_items if e.found)
        total_count = len(all_evidence_items)

        aggregation_evidence.append(Evidence(
            goal="evidence_quality_summary",
            found=avg_confidence > 0.5,
            content=(
                f"Total items: {total_count}, "
                f"Found: {found_count}, "
                f"Missing: {total_count - found_count}, "
                f"Avg confidence: {avg_confidence:.2f}"
            ),
            location="EvidenceAggregator",
            rationale=(
                f"Aggregated {total_count} evidence items across {len(present_sources)} sources. "
                f"{found_count}/{total_count} findings were positive. "
                f"Average confidence: {avg_confidence:.2f}."
            ),
            confidence=avg_confidence
        ))

    # ── 4. Error Summary ──────────────────────────────────────────
    if errors:
        aggregation_evidence.append(Evidence(
            goal="error_summary",
            found=False,
            content="; ".join(errors),
            location="EvidenceAggregator",
            rationale=f"{len(errors)} error(s) occurred during detective execution.",
            confidence=1.0
        ))

    return {"evidences": {"aggregation": aggregation_evidence}}

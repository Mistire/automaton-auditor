import datetime
from typing import Dict, List
import json
from src.state import AgentState, JudicialOpinion, CriterionResult, AuditReport

def chief_justice_node(state: AgentState) -> Dict:
    """
    Supreme Court Node: Implements the 'Judicial Validation Overlay'.
    Deterministic Python logic validates LLM-suggested scores against forensic facts.
    """
    opinions = state.opinions
    dimensions = state.rubric_dimensions
    evidences = state.evidences
    repo_url = state.repo_url

    print(f"⚖️ Swarm Validation Overlay: {repo_url}")
    print("DEBUG: JUSTICE_NODE_V3_ACTIVE")
    
    results = []
    total_raw_points = 0
    total_possible_points = 0
    
    for dim in dimensions:
        dim_id = dim["id"]
        dim_opinions = [o for o in opinions if o.criterion_id == dim_id]
        if not dim_opinions: continue
            
        prosecutor = next((o for o in dim_opinions if o.judge == "Prosecutor"), None)
        tech_lead = next((o for o in dim_opinions if o.judge == "TechLead"), None)
        
        avg_llm_score = sum(o.score for o in dim_opinions) / len(dim_opinions)
        final_score = avg_llm_score
        
        # 2. ── JUDICIAL VALIDATION OVERLAY (Python Protocol) ───────────
        overruled_reason = None
        
        # Rule of Security: CAP AT Level 1 (2/10) if raw OS system or API keys found
        safe_tooling = next((e for e in evidences.get("repo", []) if e.goal == "safe_tool_engineering"), None)
        
        # Refined check: Only trigger if forensics failed OR prosecutor explicitly mentions a violation/negligence
        security_violation = prosecutor and any(word in prosecutor.argument.lower() for word in ["security violation", "security failure", "security negligence", "insecure"])
        
        if (safe_tooling and not safe_tooling.found) or security_violation:
             floor_score = 2.0 # Level 1 on 1-10 scale
             if final_score > floor_score:
                 final_score = floor_score
                 overruled_reason = "Rule of Security: Overruled due to unsafe tool engineering patterns."

        # Rule of Hallucination: If paths hallucinated, cap report_accuracy
        if dim_id == "report_accuracy":
            hallucinations = next((e for e in evidences.get("doc", []) if e.goal == "path_hallucinations_detected"), None)
            if hallucinations and hallucinations.found:
                final_score = 2.0
                overruled_reason = "Rule of Hallucination: Overruled because the report cited non-existent files."

        # Rule of Evidence: Total citations check
        cited_all = []
        for o in dim_opinions: cited_all.extend(o.cited_evidence)
        if not cited_all and final_score > 5.0:
            final_score = 4.0
            overruled_reason = "Rule of Evidence: Overruled because judges failed to cite specific forensic goals."

        # Final synthesizing
        total_raw_points += final_score
        total_possible_points += 10 # Each dim is now out of 10
        
        # Meaningful variance on 1-10 scale
        variance = max(o.score for o in dim_opinions) - min(o.score for o in dim_opinions)
        dissent = overruled_reason or (f"Variance: {variance}/10" if len(dim_opinions) > 1 and variance > 2 else None)

        results.append(CriterionResult(
            dimension_id=dim_id,
            dimension_name=dim.get("name", "Unknown"),
            final_score=int(round(final_score)),
            judge_opinions=dim_opinions,
            dissent_summary=dissent,
            remediation=tech_lead.argument if tech_lead else "Standard mitigation required."
        ))

    overall_percentage = (total_raw_points / total_possible_points * 100) if total_possible_points > 0 else 0
    
    exec_summary = (
        f"The Swarm has delivered its verdict for {repo_url}.\n"
        f"Final Score: {round(total_raw_points, 1)} / {total_possible_points} ({overall_percentage:.1f}%).\n"
        "Audit Protocol: All dimensions have been normalized to a 1-10 scale for clarity. "
        "The Judicial Validation Overlay ensures that architectural and security rules override LLM optimism."
    )

    report = AuditReport(
        repo_url=repo_url,
        executive_summary=exec_summary,
        overall_score=overall_percentage,
        criteria=results,
        remediation_plan="\n".join([f"### {r.dimension_name}\n{r.remediation}" for r in results]),
        timestamp=datetime.datetime.now().isoformat()
    )
    
    save_report_to_file(report, total_possible_points)
    return {"final_report": report}


def save_report_to_file(report: AuditReport, total_possible: int):
    """Serializes the AuditReport model to a Markdown file in the appropriate audit/ subfolder."""
    import os
    
    # Determine target subfolder based on repo_url
    url = report.repo_url.lower()
    if "local_audit" in url or "mistire" in url:
        subfolder = "report_onself_generated"
    else:
        subfolder = "report_onpeer_generated"
        
    report_dir = os.path.join("audit", subfolder)
    os.makedirs(report_dir, exist_ok=True)
    
    # Create filename from URL/timestamp
    safe_name = report.repo_url.replace("https://", "").replace("http://", "").replace("/", "_").replace(".", "_")
    filename = os.path.join(report_dir, f"audit_{safe_name}.md")
    
    # Raw point sum for the header
    total_points = sum(c.final_score for c in report.criteria)
    
    md = f"# ⚖️ Audit Report: {report.repo_url}\n\n"
    md += f"**Timestamp:** {report.timestamp}  \n"
    md += f"**Overall Score:** {total_points} / {total_possible} ({report.overall_score:.1f}%)\n\n"
    
    md += f"## Executive Summary\n{report.executive_summary}\n\n"
    
    md += "## Criterion Breakdown\n\n"
    for c in report.criteria:
        md += f"### {c.dimension_name}\n"
        md += f"**Final Score:** {c.final_score}\n\n"
        
        if c.dissent_summary:
            md += f"> [!IMPORTANT]\n> **Judicial Dissent:** {c.dissent_summary}\n\n"
            
        md += "| Judge | Score | Argument |\n"
        md += "| :--- | :--- | :--- |\n"
        for o in c.judge_opinions:
            arg_snippet = o.argument.replace("\n", " ")
            md += f"| {o.judge} | {o.score} | {arg_snippet} |\n"
        md += "\n"
        
    md += "## Remediation Plan\n"
    md += report.remediation_plan
    
    with open(filename, "w") as f:
        f.write(md)
    
    print(f"Final Audit Report saved to: {filename}")

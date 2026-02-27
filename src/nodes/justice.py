import datetime
from typing import Dict, List
from src.state import AgentState, JudicialOpinion, CriterionResult, AuditReport


def chief_justice_node(state: AgentState) -> Dict:
    """
    Supreme Court Node: Synthesizes a final verdict from the conflicting
    opinions of the parallel judges using deterministic Python logic.
    
    Implements:
    - Rule of Security (Overrides effort)
    - Rule of Evidence (Fact supremacy over opinion)
    - Rule of Functionality (Weights Tech Lead's architectural judgment)
    - Dissent summary for high-variance criteria
    """
    opinions = state.opinions
    dimensions = state.rubric_dimensions
    evidences = state.evidences
    repo_url = state.repo_url

    print(f"⚖️ Chief Justice Node: Synthesizing verdict for {repo_url}")
    
    results = []
    
    for dim in dimensions:
        dim_id = dim["id"]
        dim_opinions = [o for o in opinions if o.criterion_id == dim_id]
        
        if not dim_opinions:
            continue
            
        prosecutor = next((o for o in dim_opinions if o.judge == "Prosecutor"), None)
        defense = next((o for o in dim_opinions if o.judge == "Defense"), None)
        tech_lead = next((o for o in dim_opinions if o.judge == "TechLead"), None)
        
        scores = [o.score for o in dim_opinions]
        avg_score = sum(scores) / len(scores)
        variance = max(scores) - min(scores)
        
        # ── DETERMINISTIC PROTOCOLS (New Rubric v3.0) ─────────────────
        
        final_score = avg_score
        dissent_summary = None
        remediation = tech_lead.argument if tech_lead else "Standard mitigation required."
        
        # 1. Rule of Security (CAP AT 3)
        # If any security forensics or judge flags confirmed flaws
        safe_tooling = next((e for e in evidences.get("repo", []) if e.goal == "safe_tool_engineering"), None)
        
        # Refined trigger: Must have a security keyword AND a critical score/negligence charge
        is_security_flaw = prosecutor and prosecutor.score < 15 and any(word in prosecutor.argument.lower() for word in ["security", "negligence", "unsafe", "raw shell", "os.system"])
        
        if is_security_flaw or (safe_tooling and not safe_tooling.found):
            print(f"  🚨 Security Override triggered for {dim_id}")
            final_score = min(final_score, 3) 
            remediation = f"CRITICAL SECURITY FIX REQUIRED: {prosecutor.argument if prosecutor else 'Unsafe tool usage detected.'}"
        
        # 2. Rule of Functionality (Tech Lead Highest Weight for Orchestration)
        if dim_id == "graph_orchestration" and tech_lead:
            print(f"  🏗️ Functionality Weight: Tech Lead judgment prioritized for {dim_id}")
            final_score = tech_lead.score
            
        # 3. Rule of Evidence (Fact Supremacy)
        agg_evidence = evidences.get("aggregation", [])
        doc_evidence = evidences.get("doc", [])
        completeness = next((e for e in agg_evidence if e.goal == "evidence_completeness"), None)
        hallucinations = next((e for e in doc_evidence if e.goal == "path_hallucinations_detected"), None)
        
        if defense and defense.score > 21:
             if (completeness and not completeness.found) or (hallucinations and hallucinations.found):
                print(f"  ⚖️ Evidence Supremacy: Overruling Defense for {dim_id} due to detected hallucinations/missing code.")
                final_score = min(final_score, tech_lead.score if tech_lead else 21)

        # 4. Map to Rubric Levels (Rounding to nearest valid level)
        levels = dim.get("levels", {})
        if levels:
            score_values = [v.get("score", 0) for v in levels.values()]
            if score_values:
                final_score = min(score_values, key=lambda x: abs(x - final_score))

        # 5. Dissent Summary (Required for Score Variance > 2 in 1-5 scale, or > 10 in 0-35 scale)
        if variance > 10:
            dissent_summary = (
                f"Judicial conflict detected. Prosecutor argued for {prosecutor.score if prosecutor else 'N/A'} "
                f"citing technical gaps, while Defense pushed for {defense.score if defense else 'N/A'} highlighting design intent."
            )

        # 6. 'No Exchange' Logic (Challenge Spec Optimization)
        is_no_exchange = (final_score == 0) and any("exchange" in k.lower() for k in levels.keys())

        results.append({
            "dimension_id": dim_id,
            "dimension_name": dim.get("name", "Unknown"),
            "final_score": int(final_score),
            "judge_opinions": dim_opinions,
            "dissent_summary": dissent_summary,
            "remediation": remediation,
            "max_score": max([v.get("score", 0) for v in levels.values()]) if levels else 35,
            "is_no_exchange": is_no_exchange
        })

    # ── Final Report Assembly ──────────────────────────────────────────
    
    valid_results = [r for r in results if not r["is_no_exchange"]]
    total_raw_points = sum(r["final_score"] for r in results)
    total_possible_points = sum(r["max_score"] for r in valid_results)
    
    overall_percentage = (sum(r["final_score"] for r in valid_results) / total_possible_points * 100) if total_possible_points > 0 else 0
    
    exec_summary = (
        f"The Automaton Auditor Swarm has delivered its verdict for {repo_url}. "
        f"Final Grade: {total_raw_points}/{total_possible_points} ({overall_percentage:.1f}%). "
        "The court analyzed evidence across parallel detective branches and synthesized findings through a dialectical judicial process."
    )

    criterion_results = [
        CriterionResult(
            dimension_id=r["dimension_id"],
            dimension_name=r["dimension_name"],
            final_score=r["final_score"],
            judge_opinions=r["judge_opinions"],
            dissent_summary=r["dissent_summary"],
            remediation=r["remediation"]
        ) for r in results
    ]

    report = AuditReport(
        repo_url=repo_url,
        executive_summary=exec_summary,
        overall_score=overall_percentage,
        criteria=criterion_results,
        remediation_plan="\n".join([f"### {r['dimension_name']}\n{r['remediation']}" for r in results]),
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

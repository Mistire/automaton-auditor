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
    opinions = state.get("opinions", [])
    dimensions = state.get("rubric_dimensions", [])
    evidences = state.get("evidences", {})
    repo_url = state.get("repo_url", "Unknown")

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
        
        # ── DETERMINISTIC PROTOCOLS ──────────────────────────────────
        
        final_score = avg_score
        dissent_summary = None
        remediation = tech_lead.argument if tech_lead else "Standard mitigation required."
        
        # 1. Rule of Security (Protocol B.2)
        # If Prosecutor cites 'Security Negligence' or 'os.system', override all.
        if prosecutor and ("security" in prosecutor.argument.lower() or "os.system" in prosecutor.argument.lower()):
            if "negligence" in prosecutor.argument.lower() or prosecutor.score <= 7:
                print(f"  ⚠️ Security Override triggered for {dim_id}")
                final_score = min(final_score, 7) # Cap at level 1/2
                remediation = f"CRITICAL SECURITY FIX REQUIRED: {prosecutor.argument}"
        
        # 2. Rule of Functionality (Protocol B.2)
        # Tech Lead weight 50% for technical criteria
        if tech_lead:
            # Weighted synthesis: TechLead is the tie-breaker
            final_score = (tech_lead.score * 0.5) + (avg_score * 0.5)
            
        # 3. Rule of Evidence (Protocol B.3)
        # Cross-reference: if defense claims something that aggregator marked as missing 
        # or if DocAnalyst found hallucinations.
        agg_evidence = evidences.get("aggregation", [])
        doc_evidence = evidences.get("doc", [])
        completeness = next((e for e in agg_evidence if e.goal == "evidence_completeness"), None)
        hallucinations = next((e for e in doc_evidence if e.goal == "path_hallucinations_detected"), None)
        
        if defense and defense.score > 25:
             if (completeness and not completeness.found) or hallucinations:
                print(f"  ⚖️ Evidence Supremacy: Overruling Defense for {dim_id} due to inconsistencies/hallucinations")
                final_score = min(final_score, tech_lead.score if tech_lead else 21)

        # 4. Map to Rubric Levels (Rounding to nearest valid level)
        levels = dim.get("levels", {})
        if levels:
            score_values = [v.get("score", 0) for v in levels.values()]
            if score_values:
                final_score = min(score_values, key=lambda x: abs(x - final_score))

        # 5. Dissent Summary (PRD Requirement: Variance > 2 for score 1-5, or > 10 for score 0-35)
        if variance > 10:
            dissent_summary = (
                f"Judicial conflict detected. Prosecutor argued for {prosecutor.score if prosecutor else 'N/A'} "
                f"citing gaps, while Defense pushed for {defense.score if defense else 'N/A'} highlighting intent."
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
    """Serializes the AuditReport model to a Markdown file in the audit/ folder."""
    import os
    
    report_dir = "audit/reports_generated"
    os.makedirs(report_dir, exist_ok=True)
    
    # Create filename from URL/timestamp
    safe_name = report.repo_url.replace("https://", "").replace("http://", "").replace("/", "_").replace(".", "_")
    filename = f"{report_dir}/audit_{safe_name}.md"
    
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

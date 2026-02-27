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
    
    results = []
    
    for dim in dimensions:
        dim_id = dim["id"]
        # Filter opinions for this specific dimension
        dim_opinions = [o for o in opinions if o.criterion_id == dim_id]
        
        if not dim_opinions:
            continue
            
        # Extract scores
        prosecutor = next((o for o in dim_opinions if o.judge == "Prosecutor"), None)
        defense = next((o for o in dim_opinions if o.judge == "Defense"), None)
        tech_lead = next((o for o in dim_opinions if o.judge == "TechLead"), None)
        
        scores = [o.score for o in dim_opinions]
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)
        variance = max_score - min_score
        
        # ── DETERMINISTIC RULES ──────────────────────────────────────
        
        final_score = avg_score # Default start
        dissent_summary = None
        
        # 1. Rule of Security: If Prosecutor cites security negligence, cap at 3 (Partial/Superficial)
        # We look for keywords in prosecutor's argument or a very low score
        if prosecutor and ("security" in prosecutor.argument.lower() or "negligence" in prosecutor.argument.lower()):
            if prosecutor.score < 3:
                final_score = min(final_score, 12 if "development_progress" in dim_id else 7) # Using rubric levels
                # Adjustment for specific rubric levels (7, 12, 15 etc)
                # Let's just use a relative cap or the tech lead's score if it's lower.
        
        # 2. Rule of Functionality: Weight Tech Lead's judgment 50% for technical criteria
        if tech_lead:
            # Simple weighted average: (TL * 2 + P + D) / 4
            final_score = (tech_lead.score * 2 + (prosecutor.score if prosecutor else tech_lead.score) + (defense.score if defense else tech_lead.score)) / 4

        # 3. Rule of Evidence: Fact Supremacy
        # If Defense gives a high score but evidence shows 'found=False' for critical items
        agg_evidence = evidences.get("aggregation", [])
        completeness = next((e for e in agg_evidence if e.goal == "evidence_completeness"), None)
        if completeness and not completeness.found and defense and defense.score > 20:
             final_score = min(final_score, tech_lead.score if tech_lead else avg_score)

        # 4. Score Normalization to Rubric Levels
        # Map the continuous average back to the closest valid discrete rubric level if possible
        levels = dim.get("levels", {})
        if levels:
            score_values = [l["score"] for l in levels.values()]
            if score_values:
                # Find the closest level
                final_score = min(score_values, key=lambda x: abs(x - final_score))

        # 5. Dissent Summary Requirement
        if variance > 10: # High variance for point-based rubric (e.g. 35 vs 7)
            dissent_summary = (
                f"The Judges were deeply divided on this criterion. "
                f"The Prosecutor argued: '{prosecutor.argument[:100]}...' "
                f"While the Defense countered: '{defense.argument[:100]}...'"
            )

        results.append(CriterionResult(
            dimension_id=dim_id,
            dimension_name=dim.get("name", "Unknown"),
            final_score=int(final_score),
            judge_opinions=dim_opinions,
            dissent_summary=dissent_summary,
            remediation=tech_lead.argument if tech_lead else "Consult a senior engineer."
        ))

    # Calculate overall stats
    overall_score = sum(r.final_score for r in results) / len(results) if results else 0
    
    # Generate Executive Summary via a small internal logic or just use a template
    exec_summary = (
        f"The Automaton Auditor has completed its swarm analysis of {repo_url}. "
        f"The court finds a total average score of {overall_score:.2f} across {len(results)} dimensions. "
    )
    if any(r.dissent_summary for r in results):
        exec_summary += "Significant judicial dissent was noted in several areas, requiring manual review."

    # Build final report
    report = AuditReport(
        repo_url=repo_url,
        executive_summary=exec_summary,
        overall_score=overall_score,
        criteria=results,
        remediation_plan="\n".join([f"### {r.dimension_name}\n{r.remediation}" for r in results]),
        timestamp=datetime.datetime.now().isoformat()
    )
    
    # Generate Markdown File
    save_report_to_file(report)
    
    return {"final_report": report}


def save_report_to_file(report: AuditReport):
    """Serializes the AuditReport model to a Markdown file in the audit/ folder."""
    import os
    
    report_dir = "audit/reports_generated"
    os.makedirs(report_dir, exist_ok=True)
    
    # Create filename from URL/timestamp
    safe_name = report.repo_url.replace("https://", "").replace("http://", "").replace("/", "_").replace(".", "_")
    filename = f"{report_dir}/audit_{safe_name}.md"
    
    md = f"# ⚖️ Audit Report: {report.repo_url}\n\n"
    md += f"**Timestamp:** {report.timestamp}  \n"
    md += f"**Overall Score:** {report.overall_score:.2f} / 35.0\n\n"
    
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

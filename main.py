import os
import json
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.graph import graph
from src.state import AgentState


def run_audit(repo_url: str, pdf_path: str = ""):
    """Runs the detective audit graph against a repo and PDF."""
    
    # Load rubric constitution
    rubric_path = os.path.join(os.path.dirname(__file__), "rubric", "week2_rubric.json")
    with open(rubric_path, "r") as f:
        rubric_data = json.load(f)

    initial_state: AgentState = {
        "repo_url": repo_url,
        "pdf_path": pdf_path,
        "rubric_dimensions": rubric_data.get("dimensions", []),
        "evidences": {},
        "opinions": [],
        "final_report": None,
        "errors": []
    }

    print(f"\n🚀 Starting Auditor Swarm on: {repo_url}")
    if pdf_path:
        print(f"📄 Including PDF report: {pdf_path}")
    
    print("🔍 Detectives fanning out...")
    
    # Execute graph
    result = graph.invoke(initial_state)

    if result.get("errors"):
        print("\n❌ Errors encountered:")
        for err in result["errors"]:
            print(f"  - {err}")
    
    # Print evidence summaries
    print("\n" + "="*50)
    print("🔎 FORENSIC EVIDENCE SUMMARY")
    print("="*50)
    
    all_evidences = result.get("evidences", {})
    if not all_evidences:
        print("No evidence collected.")
    
    for source, evidence_list in all_evidences.items():
        print(f"\n📍 {source.upper()} ANALYSIS")
        for e in evidence_list:
            status = "✅ FOUND" if e.found else "❌ MISSING"
            print(f"  [{e.confidence:>3.0%}] {status:<8} | {e.goal}")
            print(f"      Rationale: {e.rationale}")
            if e.content:
                # Truncate content for display
                snippet = e.content[:150].replace("\n", " ").strip()
                print(f"      Snippet:   {snippet}...")
    
    print("\n" + "="*50)
    print("🏁 Audit Complete")
    print("="*50)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Automaton Auditor")
    parser.add_argument("--repo_url", required=True, help="GitHub Repository URL")
    parser.add_argument("--pdf_path", default="", help="Path to architectural PDF report")
    parser.add_argument("--local_repo_path", default="", help="Optional: Path to already cloned local repository")
    
    args = parser.parse_args()
    
    # Update state handling in run_audit to respect local_repo_path
    def run_audit_local(repo_url, pdf_path, local_path):
        rubric_path = os.path.join(os.path.dirname(__file__), "rubric", "week2_rubric.json")
        with open(rubric_path, "r") as f:
            rubric_data = json.load(f)

        initial_state: AgentState = {
            "repo_url": repo_url,
            "pdf_path": pdf_path,
            "local_repo_path": local_path,
            "rubric_dimensions": rubric_data.get("dimensions", []),
            "evidences": {},
            "opinions": [],
            "final_report": None,
            "errors": []
        }
        print(f"\n🚀 Starting Adaptive Auditor Swarm on: {repo_url}")
        result = graph.invoke(initial_state)
        
        if result.get("errors"):
            print("\n❌ Errors encountered:")
            for err in result["errors"]:
                print(f"  - {err}")

        # ... printing results logic ...
        all_evidences = result.get("evidences", {})
        for source, evidence_list in all_evidences.items():
            print(f"\n📍 {source.upper()} ANALYSIS")
            for e in evidence_list:
                status = "✅ FOUND" if e.found else "❌ MISSING"
                print(f"  [{e.confidence:>3.0%}] {status:<8} | {e.goal}")
                print(f"      Rationale: {e.rationale}")
        
        if result.get("final_report"):
            report = result["final_report"]
            print(f"\n🏆 FINAL SCORE: {report.overall_score:.1f}%")

    run_audit_local(args.repo_url, args.pdf_path, args.local_repo_path)

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
    if len(sys.argv) < 2:
        print("Usage: python main.py <GITHUB_REPO_URL> [PDF_PATH]")
        sys.exit(1)
    
    repo_url = sys.argv[1]
    pdf_path = sys.argv[2] if len(sys.argv) > 2 else ""
    run_audit(repo_url, pdf_path)

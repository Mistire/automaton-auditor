import os
import sys
from dotenv import load_dotenv
import json
from src.graph import graph

def run_local_audit():
    load_dotenv()
    
    # Load rubric constitution
    rubric_path = os.path.join(os.path.dirname(__file__), "rubric", "week2_rubric.json")
    with open(rubric_path, "r") as f:
        rubric = json.load(f)
    
    # In local mode, we use the current working directory as the target
    current_dir = os.getcwd()
    
    print(f"\n🏠 Starting LOCAL Auditor Swarm on: {current_dir}")
    print("🚀 No cloning required. Benchmarking local workspace.\n")
    
    initial_state = {
        "repo_url": "LOCAL_AUDIT_WORKSPACE",
        "pdf_path": None, # Will be auto-discovered in current_dir/reports/
        "local_repo_path": current_dir,
        "rubric_dimensions": rubric["dimensions"],
        "evidences": {},
        "opinions": [],
        "errors": []
    }
    
    try:
        # Run the graph
        result = graph.invoke(initial_state)
        
        # Print high-level summary
        report = result.get("final_report")
        if report:
            print(f"\n✅ Audit Complete!")
            print(f"📊 Overall Score: {report.overall_score:.1f}%")
            print(f"📄 Summary: {report.executive_summary[:200]}...")
            print(f"\n📂 Final report saved to audit/reports_generated/")
        else:
            errors = result.get("errors", [])
            print(f"\n❌ Audit Failed or Aborted.")
            for err in errors:
                print(f"   - {err}")

    except Exception as e:
        print(f"\n💥 Global Swarm Failure: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_local_audit()

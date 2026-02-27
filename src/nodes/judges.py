import json
import os
from typing import Dict, List, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from src.state import AgentState, JudicialOpinion


from src.tools.llm_tools import get_llm


def create_judge_node(judge_persona: str, judge_name: str):
    """
    Factory function to create judge nodes with specific personas.
    Each node evaluates the same evidence through a unique lens.
    """
    
    def judge_node(state: AgentState) -> Dict:
        # Initialize model with structured output enforcement
        llm = get_llm()
        structured_llm = llm.with_structured_output(JudicialOpinion)
        
        dimensions = state.get("rubric_dimensions", [])
        evidences = state.get("evidences", {})
        
        # Flatten evidence into a readable, concise context
        evidence_context = ""
        for source, items in evidences.items():
            found_items = [e for e in items if e.found]
            missing_items = [e for e in items if not e.found]
            
            evidence_context += f"\nSOURCE: {source.upper()}\n"
            for e in found_items:
                evidence_context += f"✅ {e.goal} ({e.location}): {e.rationale}\n"
                if e.content:
                    evidence_context += f"  > {e.content[:150].strip()}...\n"
            for e in missing_items:
                evidence_context += f"❌ Missing: {e.goal}\n"

        opinions = []
        for dim in dimensions:
            prompt = f"""
            You are acting as the {judge_name} in a Digital Courtroom audit.
            
            YOUR PERSONA:
            {judge_persona}
            
            THE CONSTITUTION (Rubric Dimension to evaluate):
            ID: {dim.get('id')}
            Name: {dim.get('name', 'Unknown')}
            Forensic Instruction: {dim.get('forensic_instruction', 'Follow global standards')}
            
            Levels for scoring:
            {json.dumps(dim.get('levels', {}), indent=2)}
            
            FORENSIC EVIDENCE COLLECTED BY DETECTIVES:
            {evidence_context}
            
            ASSIGNMENT:
            Evaluate the evidence against this specific rubric dimension. 
            1. Render a score (typically 0, 7, 21, 35 as per the levels provided). Use the most appropriate level.
            2. Provide a detailed philosophical and technical argument from your unique perspective.
            3. Cite the specific evidence 'goals' or 'locations' you relied on.
            
            Respond strictly in the required JSON format.
            """
            
            try:
                # Invoke LLM with retries for structured output (handled by library/prompt)
                opinion = structured_llm.invoke(prompt)
                
                # Ensure metadata is strictly correct even if LLM hallucinates these fields
                opinion.judge = judge_name
                opinion.criterion_id = dim.get('id')
                
                opinions.append(opinion)
            except Exception as e:
                # Return an error opinion if LLM fails, so the Chief Justice can see the failure
                opinions.append(JudicialOpinion(
                    judge=judge_name,
                    criterion_id=dim.get('id', 'unknown'),
                    score=0,
                    argument=f"ERROR: Failed to render opinion. {str(e)}",
                    cited_evidence=[]
                ))
                
        return {"opinions": opinions}
    
    return judge_node


# ── Prosecutor Persona ────────────────────────────────────────────────
PROSECUTOR_PERSONA = """
CORE PHILOSOPHY: 'Trust No One. Assume Vibe Coding.'
OBJECTIVE: Scrutinize the evidence for gaps, security flaws, laziness, and architectural deception.
STATUTE OF ORCHESTRATION: If the flow is linear or lacks a synchronization node (fan-in), charge 'Orchestration Fraud' (Max Score 1).
STATUTE OF ENGINEERING: If 'os.system' or raw shell commands are found, charge 'Security Negligence' (Max Score 3 as per Rule 1).
STRATEGY: Be adversarial. Specifically look for 'Failure Patterns': single init commits, plain dicts instead of Pydantic, linear graph flow, or hallucinated file paths in the report.
Charge the defendant with 'Hallucination Liability' if their report claims features or file paths that the 'path_hallucinations_detected' evidence confirms are missing.
"""

# ── Defense Attorney Persona ──────────────────────────────────────────
DEFENSE_PERSONA = """
CORE PHILOSOPHY: 'Reward Effort and Intent. Look for the Spirit of the Law.'
OBJECTIVE: Highlight creative workarounds, deep thought, and iterative effort.
STATUTE OF EFFORT: If the git history shows clear progression (Environment -> Tooling -> Graph), argue for 'Success Pattern: Iterative Excellence' (Boost score toward 35).
STRATEGY: Be optimistic. If code is functional and evidence shows 'functional reducers' or 'distinct parallel personas', argue for 'Deep Code Comprehension'.
Interpret ambiguous evidence (e.g., placeholder snippets) as proof of intent rather than neglect. Focus on 'Success Patterns' like TypedDict/BaseModel usage and fan-out mastery.
"""

# ── Tech Lead Persona ─────────────────────────────────────────────────
TECH_LEAD_PERSONA = """
CORE PHILOSOPHY: 'Does it actually work? Is it maintainable and architecturally sound?'
OBJECTIVE: Evaluate technical rigor, modularity, and practical viability.
STATUTE OF ENGINEERING: If the system uses Pydantic models with reducers and structured output, rule 'Architectural Soundness' (Target 35). If 'Dict Soups' or unvalidated output are used, rule 'Technical Debt' (Max Score 7).
STRATEGY: Be pragmatic. Value 'Verified Paths' over 'Hallucinated' ones. Focus on the 'Success Pattern': START -> [Parallel Detectives] -> Aggregator -> [Parallel Judges] -> Synthesis.
You are the technical tie-breaker. Your assessment of 'Graph Orchestration' and 'State Management' carries the most authority in the final synthesis.
"""

# Exported nodes
prosecutor_node = create_judge_node(PROSECUTOR_PERSONA, "Prosecutor")
defense_node = create_judge_node(DEFENSE_PERSONA, "Defense")
tech_lead_node = create_judge_node(TECH_LEAD_PERSONA, "TechLead")

import json
import os
from typing import Dict, List, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from src.state import AgentState, JudicialOpinion


def get_llm():
    """
    Factory to initialize the appropriate LLM based on environment configuration.
    Supports Google Gemini (native) and OpenRouter (OpenAI-compatible).
    """
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    if provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-lite-preview-09-2025:free")
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.1,
            max_tokens=2000
        )
    else:
        # Default to Gemini
        api_key = os.getenv("GOOGLE_API_KEY")
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", 
            google_api_key=api_key,
            temperature=0.1
        )


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
STRATEGY: Be adversarial. If a file is missing or a pattern is weak, penalize heavily. 
Look for bypassed structure (e.g., using plain dicts instead of Pydantic).
Charge the defendant with 'Hallucination Liability' if their report claims features the code doesn't have.
"""

# ── Defense Attorney Persona ──────────────────────────────────────────
DEFENSE_PERSONA = """
CORE PHILOSOPHY: 'Reward Effort and Intent. Look for the Spirit of the Law.'
OBJECTIVE: Highlight creative workarounds, deep thought, and iterative effort.
STRATEGY: Be optimistic. If the code is imperfect but the git history shows genuine struggle and progression, argue for a higher score.
Focus on strengths and the 'why' behind decisions. Interpret ambiguous evidence in the developer's favor.
"""

# ── Tech Lead Persona ─────────────────────────────────────────────────
TECH_LEAD_PERSONA = """
CORE PHILOSOPHY: 'Does it actually work? Is it maintainable and architecturally sound?'
OBJECTIVE: Evaluate technical rigor, modularity, and practical viability.
STRATEGY: Be pragmatic and objective. Ignore the 'Vibe' and the 'Struggle'. 
Focus on whether the system uses correct patterns (e.g., parallel fan-out, state reducers, sandboxing).
You are the technical tie-breaker. Assess the 'Technical Debt' realistically.
"""

# Exported nodes
prosecutor_node = create_judge_node(PROSECUTOR_PERSONA, "Prosecutor")
defense_node = create_judge_node(DEFENSE_PERSONA, "Defense")
tech_lead_node = create_judge_node(TECH_LEAD_PERSONA, "TechLead")

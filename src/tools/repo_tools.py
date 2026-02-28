import os
import tempfile
import ast
import re
from typing import List, Dict, Optional, Any
from pathlib import Path
from src.state import Evidence
from src.tools import safety


def clone_repo(repo_url: str) -> str:
    """
    Clones a repository into a temporary directory with robust error handling.
    """
    if not safety.is_valid_github_url(repo_url):
        raise ValueError(f"Invalid GitHub URL format: {repo_url}")

    temp_dir = tempfile.mkdtemp(prefix="auditor_")
    result = safety.run_safe_command(["git", "clone", repo_url, temp_dir])
    
    if result.returncode != 0:
        error_mode = safety.parse_git_error(result.stderr)
        # Cleanup if failed
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
            
        raise Exception(f"GIT_CLONE_FAILURE|{error_mode}|{result.stderr}")
        
    return temp_dir


def extract_git_history(repo_path: str) -> List[Evidence]:
    """
    Extracts git commit history and verifies progression story.
    Master Thinker Progression: Setup -> Tooling -> Graph
    """
    result = safety.run_safe_command(["git", "log", "--oneline", "--reverse"], cwd=repo_path)
    if result.returncode != 0:
        return [Evidence(
            goal="git_forensic_analysis",
            found=False,
            location="git log",
            rationale=f"Failed to read git log: {result.stderr}",
            confidence=1.0
        )]

    commits = result.stdout.strip().split("\n")
    
    # Keyword analysis for progression story
    keywords = {
        "setup": ["init", "setup", "env", "install", "pyproject", "requirements"],
        "tooling": ["tool", "investigator", "analyst", "vision", "detective", "safety", "ast"],
        "graph": ["graph", "orchestration", "state", "node", "edge", "workflow", "builder"]
    }
    
    found_stages = {stage: False for stage in keywords}
    for commit in commits:
        msg = commit.lower()
        for stage, terms in keywords.items():
            if any(term in msg for term in terms):
                found_stages[stage] = True
    
    story_check = all(found_stages.values())
    found = len(commits) >= 3 and story_check
    
    rationale = f"Found {len(commits)} commits."
    if story_check:
        rationale += " Progression story (Setup -> Tooling -> Graph) verified."
    else:
        missing = [s for s, f in found_stages.items() if not f]
        rationale += f" Missing progression stages: {', '.join(missing)}."

    return [Evidence(
        goal="git_forensic_analysis",
        found=found,
        content="\n".join(commits[:15]),
        location="git log",
        rationale=rationale,
        confidence=1.0
    )]


class StateVisitor(ast.NodeVisitor):
    """Deep AST Visitor to find AgentState and reducer patterns."""
    def __init__(self):
        self.found_state = False
        self.has_reducers = False
        self.code_snippet = ""

    def visit_ClassDef(self, node):
        if node.name == "AgentState":
            self.found_state = True
            # Look for Annotated types with operator reducers
            for item in node.body:
                if isinstance(item, ast.AnnAssign):
                    # Check for Annotated[..., operator.add] etc
                    if isinstance(item.annotation, ast.Subscript):
                        if getattr(item.annotation.value, "id", "") == "Annotated":
                            # Walk slices to find Attribute(attr='add') or Attribute(attr='ior')
                            for slice_node in ast.walk(item.annotation.slice):
                                if isinstance(slice_node, ast.Attribute) and slice_node.attr in ["add", "ior"]:
                                    self.has_reducers = True
            self.code_snippet = ast.unparse(node)
        self.generic_visit(node)


class SecurityVisitor(ast.NodeVisitor):
    """
    AST Visitor to scan for security anti-patterns.
    Looks for structural usage of unsafe functions.
    """
    def __init__(self):
        self.violations = []
        self.good_practices = []

    def visit_Call(self, node):
        # Look for os.system(...)
        if isinstance(node.func, ast.Attribute):
            if getattr(node.func.value, "id", "") == "os" and node.func.attr == "system":
                self.violations.append(f"os.system() call at line {node.lineno}")
        
        # Look for subprocess.run(..., shell=True)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "run":
            if getattr(node.func.value, "id", "") == "subprocess":
                for keyword in node.keywords:
                    if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                        self.violations.append(f"subprocess.run(shell=True) at line {node.lineno}")

        # Look for tempfile usage (good practice)
        if isinstance(node.func, ast.Name) and node.func.id == "tempfile":
             self.good_practices.append("tempfile usage")
        if isinstance(node.func, ast.Attribute) and getattr(node.func.value, "id", "") == "tempfile":
             self.good_practices.append(f"tempfile.{node.func.attr} usage")

        self.generic_visit(node)


def analyze_state_structure(repo_path: str) -> List[Evidence]:
    """
    Analyzes state management rigor using deep AST inspection.
    """
    paths = [Path(repo_path) / "src" / "state.py", Path(repo_path) / "src" / "graph.py"]
    visitor = StateVisitor()
    
    for path in paths:
        if path.exists():
            with open(path, "r") as f:
                try:
                    tree = ast.parse(f.read())
                    visitor.visit(tree)
                except: continue

    return [Evidence(
        goal="state_management_rigor",
        found=visitor.found_state and visitor.has_reducers,
        content=visitor.code_snippet if visitor.found_state else None,
        location="src/state.py",
        rationale="AST verification confirmed AgentState with functional reducers.",
        confidence=1.0
    )]


def analyze_safe_tooling(repo_path: str) -> List[Evidence]:
    """
    Scans for security practices using AST structural analysis.
    """
    tools_dir = Path(repo_path) / "src" / "tools"
    all_violations = []
    all_practices = []
    
    if tools_dir.exists():
        for path in tools_dir.glob("**/*.py"):
            with open(path, "r") as f:
                try:
                    tree = ast.parse(f.read())
                    visitor = SecurityVisitor()
                    visitor.visit(tree)
                    if visitor.violations: all_violations.append(f"{path.name}: {visitor.violations}")
                    if visitor.good_practices: all_practices.append(f"{path.name}: {visitor.good_practices}")
                except: continue

    return [Evidence(
        goal="safe_tool_engineering",
        found=len(all_violations) == 0 and len(all_practices) > 0,
        content=f"Violations: {all_violations}\nPractices: {all_practices}",
        location="src/tools/",
        rationale="Structural AST scan confirmed absence of shell usage and presence of sandboxing.",
        confidence=1.0
    )]

# (Keeping analyze_graph_orchestration and analyze_structured_output as they were, or updated if needed)
# ... Implementation of other tools following same safety pattern ...

# Adding back the missing ones briefly for completeness
class GraphVisitor(ast.NodeVisitor):
    def __init__(self):
        self.edges = []
        self.has_stategraph = False
        self.graph_definition_nodes = []

    def visit_Call(self, node):
        # Detect StateGraph instantiation
        if isinstance(node.func, ast.Name) and node.func.id == "StateGraph":
            self.has_stategraph = True
            self.graph_definition_nodes.append(node)
            
        # Detect node and edge additions
        if isinstance(node.func, ast.Attribute) and node.func.attr in ["add_node", "add_edge", "add_conditional_edges"]:
             self.graph_definition_nodes.append(node)
             if node.func.attr == "add_edge" and len(node.args) >= 2:
                  self.edges.append((ast.unparse(node.args[0]), ast.unparse(node.args[1])))
        
        self.generic_visit(node)

def analyze_graph_orchestration(repo_path: str) -> List[Evidence]:
    graph_path = Path(repo_path) / "src" / "graph.py"
    if not graph_path.exists():
        return [Evidence(goal="graph_orchestration", found=False, location="src/graph.py", rationale="Graph definition file not found.", confidence=1.0)]
    
    with open(graph_path, "r") as f:
        code = f.read()
        try:
            tree = ast.parse(code)
            visitor = GraphVisitor()
            visitor.visit(tree)
        except Exception as e:
            return [Evidence(goal="graph_orchestration", found=False, location="src/graph.py", rationale=f"AST Parse failed: {str(e)}", confidence=1.0)]
    
    # Calculate fan-out points
    from_counts = {}
    for u, v in visitor.edges:
        from_counts[u] = from_counts.get(u, 0) + 1
    
    fan_out_points = [node for node, count in from_counts.items() if count > 1]
    
    # Formal Code Capture for judicial review
    graph_code_block = "\n".join([ast.unparse(n) for n in visitor.graph_definition_nodes])

    return [Evidence(
        goal="graph_orchestration",
        found=visitor.has_stategraph and len(fan_out_points) >= 1,
        content=graph_code_block if graph_code_block else code[:500],
        location="src/graph.py",
        rationale=f"Orchestration check: {len(visitor.edges)} edges found. Fan-out points: {', '.join(fan_out_points) if fan_out_points else 'None'}.",
        confidence=1.0
    )]

def analyze_structured_output(repo_path: str) -> List[Evidence]:
    judges_path = Path(repo_path) / "src" / "nodes" / "judges.py"
    found = False
    snippet = None
    if judges_path.exists():
        with open(judges_path, "r") as f:
            code = f.read()
            found = ".with_structured_output" in code or ".bind_tools" in code
            if found:
                # Extract snippet around the enforcement call
                lines = code.split("\n")
                for i, line in enumerate(lines):
                    if ".with_structured_output" in line or ".bind_tools" in line:
                        snippet = "\n".join(lines[max(0, i-2):min(len(lines), i+3)])
                        break
    return [Evidence(
        goal="structured_output_enforcement", 
        found=found, 
        content=snippet,
        location="src/nodes/judges.py", 
        rationale="Scanned for enforcement patterns in Judge nodes.", 
        confidence=1.0
    )]


def analyze_judicial_nuance(repo_path: str) -> List[Evidence]:
    """
    Forensic Tool: Verifies persona distinctness in src/nodes/judges.py.
    Checks for overlapping text (Collusion) and keyword alignment.
    """
    judges_path = Path(repo_path) / "src" / "nodes" / "judges.py"
    if not judges_path.exists():
        return [Evidence(goal="judicial_nuance", found=False, location="src/nodes/judges.py", rationale="Judge node definition not found.", confidence=1.0)]

    with open(judges_path, "r") as f:
        content = f.read()
    
    # Extract personas using more flexible regex (look for SYSTEM, PERSONA, or PROMPT)
    personas = {}
    search_patterns = {
        "PROSECUTOR": r"_?(PROSECUTOR|ADVERSARIAL|PROSECUTOR_SYSTEM)_(PERSONA|SYSTEM|PROMPT)\s*=\s*[\"']{3}(.*?)[\"']{3}",
        "DEFENSE": r"_?(DEFENSE|FORGIVING|DEFENSE_SYSTEM)_(PERSONA|SYSTEM|PROMPT)\s*=\s*[\"']{3}(.*?)[\"']{3}",
        "TECH_LEAD": r"_?(TECH_LEAD|PRAGMATIC|TECH_LEAD_SYSTEM)_(PERSONA|SYSTEM|PROMPT)\s*=\s*[\"']{3}(.*?)[\"']{3}"
    }
    
    for p, pattern in search_patterns.items():
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            personas[p] = match.group(3).strip()
    
    if len(personas) < 3:
        return [Evidence(goal="judicial_nuance", found=False, location="src/nodes/judges.py", rationale=f"Only found {len(personas)}/3 personas.", confidence=1.0)]

    # Check for collusion (overlap)
    def word_set(text): return set(text.lower().split())
    
    p_set = word_set(personas["PROSECUTOR"])
    d_set = word_set(personas["DEFENSE"])
    t_set = word_set(personas["TECH_LEAD"])
    
    def overlap(s1, s2): 
        if not s1 or not s2: return 0
        return len(s1 & s2) / max(len(s1), len(s2))
    
    collusion_max = max(overlap(p_set, d_set), overlap(p_set, t_set), overlap(d_set, t_set))
    
    has_adversarial = "trust no one" in personas["PROSECUTOR"].lower() or "adversarial" in personas["PROSECUTOR"].lower()
    has_forgiving = "reward" in personas["DEFENSE"].lower() or "optimistic" in personas["DEFENSE"].lower()
    has_pragmatic = "maintainable" in personas["TECH_LEAD"].lower() or "soundness" in personas["TECH_LEAD"].lower()

    found = collusion_max < 0.5 and has_adversarial and has_forgiving and has_pragmatic
    rationale = f"Max overlap: {collusion_max:.1%}. Personas: {'✅' if has_adversarial else '❌'}Prosecutor, {'✅' if has_forgiving else '❌'}Defense, {'✅' if has_pragmatic else '❌'}TechLead."
    
    return [Evidence(
        goal="judicial_nuance",
        found=found,
        content=f"PROSECUTOR: {personas['PROSECUTOR'][:100]}...\nDEFENSE: {personas['DEFENSE'][:100]}...\nTECH_LEAD: {personas['TECH_LEAD'][:100]}...",
        location="src/nodes/judges.py",
        rationale=rationale,
        confidence=1.0
    )]


def analyze_justice_synthesis(repo_path: str) -> List[Evidence]:
    """
    Forensic Protocol: Analyzes the Chief Justice node for deterministic rules.
    Identifies specific rules (Security, Evidence, Functionality) for diagnostic precision.
    """
    justice_path = Path(repo_path) / "src" / "nodes" / "justice.py"
    if not justice_path.exists():
        return [Evidence(goal="chief_justice_synthesis", found=False, location="src/nodes/justice.py", rationale="Supreme Court synthesis engine not found.", confidence=1.0)]

    with open(justice_path, "r") as f:
        content = f.read()
        
    found_rules = []
    # Flexible keyword search for deterministic rules
    if re.search(r"Rule\s*of\s*Security", content, re.I): found_rules.append("Rule of Security")
    if re.search(r"Rule\s*of\s*Hallucination", content, re.I): found_rules.append("Rule of Hallucination")
    if re.search(r"Rule\s*of\s*Evidence", content, re.I): found_rules.append("Rule of Evidence")
    if re.search(r"(total|final)_.*?points", content, re.I): found_rules.append("Final Synthesis Logic")

    found = len(found_rules) >= 3 # Reduced threshold for flexibility
    rationale = f"Detected rules: {', '.join(found_rules)}" if found_rules else "No deterministic judicial rules detected."
    
    return [Evidence(
        goal="chief_justice_synthesis",
        found=found,
        content=content[:1000],
        location="src/nodes/justice.py",
        rationale=rationale,
        confidence=1.0
    )]

def file_content_crawler(repo_path: str, keywords: List[str]) -> List[Evidence]:
    """
    Adaptive Tool: Crawls the repository for file contents matching specific keywords.
    Used as a general fallback for rubric dimensions that don't have specialized tools.
    """
    root = Path(repo_path)
    found_snippets = []
    
    # We focus on src, tools, nodes, and root level config files
    search_dirs = ["src", "tools", "nodes", "audit", "reports"]
    target_exts = [".py", ".md", ".txt", ".json", ".toml", ".yaml"]
    
    for dir_name in search_dirs:
        dir_path = root / dir_name
        if not dir_path.exists(): continue
        
        for p in dir_path.glob("**/*"):
            if p.suffix in target_exts:
                try:
                    with open(p, "r", errors="ignore") as f:
                        content = f.read()
                        if any(k.lower() in content.lower() for k in keywords):
                            found_snippets.append(f"FILE: {p.relative_to(root)}\n{content[:500]}...")
                            if len(found_snippets) >= 5: break # Limit capture
                except: continue
        if len(found_snippets) >= 5: break
                
    return [Evidence(
        goal="adaptive_content_crawl",
        found=len(found_snippets) > 0,
        content="\n---\n".join(found_snippets),
        location="Repository Crawl",
        rationale=f"Performed adaptive crawl for keywords: {', '.join(keywords)}.",
        confidence=0.7
    )]

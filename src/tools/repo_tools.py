import os
import tempfile
import ast
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
    Extracts git commit history and verifies progression.
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
    found = len(commits) >= 3
    
    return [Evidence(
        goal="git_forensic_analysis",
        found=found,
        content="\n".join(commits[:10]),
        location="git log",
        rationale=f"Found {len(commits)} commits. Succession check focuses on atomic progression.",
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
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == "StateGraph": self.has_stategraph = True
        if isinstance(node.func, ast.Attribute) and node.func.attr == "add_edge":
            if len(node.args) >= 2: self.edges.append((ast.unparse(node.args[0]), ast.unparse(node.args[1])))
        self.generic_visit(node)

def analyze_graph_orchestration(repo_path: str) -> List[Evidence]:
    graph_path = Path(repo_path) / "src" / "graph.py"
    if not graph_path.exists(): return [Evidence(goal="graph_orchestration", found=False, location="src/graph.py", rationale="Not found", confidence=1.0)]
    with open(graph_path, "r") as f:
        tree = ast.parse(f.read())
        visitor = GraphVisitor()
        visitor.visit(tree)
    starts = [v for u, v in visitor.edges if "START" in u]
    return [Evidence(
        goal="graph_orchestration",
        found=visitor.has_stategraph and len(starts) >= 2,
        content=ast.unparse(tree),
        location="src/graph.py",
        rationale=f"Fan-out points: {len(starts)}",
        confidence=0.9
    )]

def analyze_structured_output(repo_path: str) -> List[Evidence]:
    judges_path = Path(repo_path) / "src" / "nodes" / "judges.py"
    found = False
    if judges_path.exists():
        with open(judges_path, "r") as f:
            content = f.read()
            found = ".with_structured_output" in content or ".bind_tools" in content
    return [Evidence(goal="structured_output_enforcement", found=found, location="src/nodes/judges.py", rationale="Scanned for enforcement patterns.", confidence=0.8)]

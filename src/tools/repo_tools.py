import os
import subprocess
import tempfile
import ast
from typing import List, Dict, Optional, Any
from pathlib import Path
from src.state import Evidence


def run_command(command: List[str], cwd: Optional[str] = None) -> subprocess.CompletedProcess:
    """Run a shell command safely and return the result."""
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False
    )


def clone_repo(repo_url: str) -> str:
    """
    Clones a repository into a temporary directory.
    Returns the path to the cloned repository.
    """
    temp_dir = tempfile.mkdtemp(prefix="auditor_")
    result = run_command(["git", "clone", repo_url, temp_dir])
    if result.returncode != 0:
        raise Exception(f"Failed to clone repository: {result.stderr}")
    return temp_dir


def extract_git_history(repo_path: str) -> List[Evidence]:
    """
    Extracts git commit history and verifies progression.
    """
    result = run_command(["git", "log", "--oneline", "--reverse"], cwd=repo_path)
    if result.returncode != 0:
        return [Evidence(
            goal="git_forensic_analysis",
            found=False,
            location="git log",
            rationale="Failed to read git log",
            confidence=1.0
        )]

    commits = result.stdout.strip().split("\n")
    found = len(commits) >= 3
    
    return [Evidence(
        goal="git_forensic_analysis",
        found=found,
        content="\n".join(commits[:10]), # Return first 10 for context
        location="git log",
        rationale=f"Found {len(commits)} commits. Succession check required by Judges.",
        confidence=1.0
    )]


class StateVisitor(ast.NodeVisitor):
    """AST Visitor to find AgentState and reducer patterns."""
    def __init__(self):
        self.found_state = False
        self.has_reducers = False
        self.code_snippet = ""

    def visit_ClassDef(self, node):
        if node.name == "AgentState":
            self.found_state = True
            # Check for Annotated with reducers
            for item in node.body:
                if isinstance(item, ast.AnnAssign):
                    if isinstance(item.annotation, ast.Subscript):
                        # Look for Annotated[...]
                        if getattr(item.annotation.value, "id", "") == "Annotated":
                            # Look for operator.add or operator.ior
                            for slice_item in ast.walk(item.annotation.slice):
                                if isinstance(slice_item, ast.Attribute):
                                    if slice_item.attr in ["add", "ior"]:
                                        self.has_reducers = True
            self.code_snippet = ast.unparse(node)
        self.generic_visit(node)


def analyze_state_structure(repo_path: str) -> List[Evidence]:
    """
    Analyzes src/state.py or src/graph.py for state management rigor using AST.
    """
    evidences = []
    
    # Common locations for state
    paths = [
        Path(repo_path) / "src" / "state.py",
        Path(repo_path) / "src" / "graph.py"
    ]
    
    visitor = StateVisitor()
    state_file_found = False
    
    for path in paths:
        if path.exists():
            state_file_found = True
            with open(path, "r") as f:
                try:
                    tree = ast.parse(f.read())
                    visitor.visit(tree)
                except Exception as e:
                    continue

    evidences.append(Evidence(
        goal="state_management_rigor",
        found=visitor.found_state and visitor.has_reducers,
        content=visitor.code_snippet if visitor.found_state else None,
        location="src/state.py" if state_file_found else "N/A",
        rationale="Checked for AgentState with Annotated reducers (operator.add/ior).",
        confidence=0.9
    ))
    
    return evidences


class GraphVisitor(ast.NodeVisitor):
    """AST Visitor to analyze StateGraph wiring and parallelism."""
    def __init__(self):
        self.node_count = 0
        self.edges = []
        self.has_stategraph = False
        self.parallel_detectives = False
        self.parallel_judges = False
        self.code_snippet = ""

    def visit_Call(self, node):
        # Look for StateGraph(...)
        if isinstance(node.func, ast.Name) and node.func.id == "StateGraph":
            self.has_stategraph = True
        
        # Look for builder.add_edge(...)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "add_edge":
            if len(node.args) >= 2:
                u = ast.unparse(node.args[0])
                v = ast.unparse(node.args[1])
                self.edges.append((u, v))
        
        self.generic_visit(node)


def analyze_graph_orchestration(repo_path: str) -> List[Evidence]:
    """
    Analyzes src/graph.py for parallel orchestration using AST.
    """
    graph_path = Path(repo_path) / "src" / "graph.py"
    if not graph_path.exists():
         return [Evidence(
            goal="graph_orchestration",
            found=False,
            location="src/graph.py",
            rationale="Graph file not found",
            confidence=1.0
        )]

    with open(graph_path, "r") as f:
        content = f.read()
        tree = ast.parse(content)
        visitor = GraphVisitor()
        visitor.visit(tree)

    # Check for fan-out (detectives)
    starts = [v for u, v in visitor.edges if "START" in u or "start" in u]
    parallel_detectives = len(starts) >= 2
    
    # Check for aggregation (fan-in)
    v_counts = {}
    for u, v in visitor.edges:
        v_counts[v] = v_counts.get(v, 0) + 1
    fan_in = any(count >= 2 for count in v_counts.values())

    return [Evidence(
        goal="graph_orchestration",
        found=visitor.has_stategraph and (parallel_detectives or fan_in),
        content=ast.unparse(tree), # Return full graph file for context
        location="src/graph.py",
        rationale=f"StateGraph: {visitor.has_stategraph}, Fan-out points: {len(starts)}, Fan-in points: {fan_in}",
        confidence=0.8
    )]


def analyze_safe_tooling(repo_path: str) -> List[Evidence]:
    """
    Scans for security practices (tempfile, no os.system).
    """
    violations = []
    good_practices = []
    tools_dir = Path(repo_path) / "src" / "tools"
    
    if tools_dir.exists():
        for path in tools_dir.glob("**/*.py"):
            with open(path, "r") as f:
                content = f.read()
                if "os.system" in content:
                    violations.append(str(path.relative_to(repo_path)))
                if "tempfile" in content or "TemporaryDirectory" in content:
                    good_practices.append(str(path.relative_to(repo_path)))

    return [Evidence(
        goal="safe_tool_engineering",
        found=len(violations) == 0 and len(good_practices) > 0,
        content=f"Violations: {violations}, Good Practices: {good_practices}",
        location="src/tools/",
        rationale="Scanned for os.system (violation) and tempfile (good practice).",
        confidence=0.9
    )]


def analyze_structured_output(repo_path: str) -> List[Evidence]:
    """
    Checks if judge nodes enforce structured output.
    """
    judges_path = Path(repo_path) / "src" / "nodes" / "judges.py"
    found = False
    snippet = ""
    
    if judges_path.exists():
        with open(judges_path, "r") as f:
            content = f.read()
            if ".with_structured_output" in content or ".bind_tools" in content:
                found = True
                snippet = content # Return snippet for verification

    return [Evidence(
        goal="structured_output_enforcement",
        found=found,
        content=snippet[:500] if found else None,
        location="src/nodes/judges.py",
        rationale="Checked for with_structured_output or bind_tools in judge implementations.",
        confidence=0.9
    )]

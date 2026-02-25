# Interim Architecture Report: The Automaton Auditor

> **Date:** 2026-02-25  
> **Status:** Interim Submission (Detective Layer Complete)

## 1. Executive Summary

We have successfully implemented the first half of the **Digital Courtroom** architecture for the Automaton Auditor. The system is built on a robust, observable foundation using **LangGraph** for orchestration and **uv** for dependency management. The **Detective Layer** is fully operational, capable of performing forensic analysis on both source code and documentation.

## 2. Architecture Decisions

### 2.1 State Management (Pydantic vs. Dicts)

We chose **Pydantic `BaseModel`** for all forensic and judicial data structures.

- **Rationale:** Strict type validation prevents "Dict Soup" errors where nodes pass malformed data.
- **Reducers:** We use `operator.ior` (Indexed OR) for the `evidences` dictionary to allow parallel detectives to update the state without overwriting each other's findings.

### 2.2 Forensic Analysis (AST vs. Regex)

The `RepoInvestigator` uses Python's native **`ast` (Abstract Syntax Tree)** module.

- **Rationale:** Regex is brittle and fails on complex formatting or comments. AST parsing allows the agent to verify the _structure_ of the code (e.g., confirming a class inherits from `BaseModel` or a graph uses `add_edge`) with 100% accuracy.

### 2.3 Sandboxing & Security

Repository cloning is isolated using **`tempfile.TemporaryDirectory`**.

- **Rationale:** Executing `git clone` on untrusted peer repositories poses a security risk. Sandboxing ensures that cloned code is isolated from the live environment and automatically cleaned up after the audit.

## 3. Current Implementation

### 3.1 The Detective Swarm (Fan-Out/Fan-In)

The current `StateGraph` implements a parallel fan-out architectural pattern:

1. **START** → `Parallel([RepoInvestigator, DocAnalyst, VisionInspector])`
2. **Collect** → `EvidenceAggregator` (Fan-In)
3. **Finish** → `END`

### 3.2 Implemented Components

- **`src/state.py`**: Fully typed state schema.
- **`src/tools/`**: Forensic tools for Git, AST, and PDF analysis.
- **`src/nodes/detectives.py`**: LangGraph nodes wrapping the forensic tools.
- **`rubric/week2_rubric.json`**: The machine-readable "Constitution" defining the audit rules.

## 4. Planned Roadmap (Final Submission)

### 4.1 The Judicial Layer

We will implement three parallel Judge nodes:

- **The Prosecutor:** Searching for technical debt and security violations.
- **The Defense:** Highlighting engineering effort and conceptual depth.
- **The Tech Lead:** Evaluating maintainability and pragmatic execution.

### 4.2 The Supreme Court

The `ChiefJusticeNode` will be implemented with **deterministic conflict resolution logic**, ensuring that identifying a security flaw (fact) overrules any "effort points" (opinion).

### 4.3 MinMax Feedback Loop

We will enable the auditor to audit itself, using the feedback to refine the judge prompts and detective protocols.

---

_End of Interim Report_

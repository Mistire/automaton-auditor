import re
import fitz  # PyMuPDF
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from src.state import Evidence


def ingest_pdf(pdf_path: str) -> List[Dict[str, str]]:
    """
    Parses a PDF file and returns a list of chunks (by page).
    Each chunk is a dictionary with 'text' and 'metadata'.
    """
    if not pdf_path or not Path(pdf_path).exists():
        return []

    chunks = []
    try:
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            text = page.get_text()
            chunks.append({
                "text": text,
                "metadata": {"page": i + 1, "source": str(pdf_path)}
            })
        doc.close()
    except Exception as e:
        print(f"Error parsing PDF: {e}")
    
    return chunks


def extract_file_paths(text: str) -> List[str]:
    """
    Extracts potential file paths from text using regex.
    Matches common project structures like src/..., reports/..., etc.
    """
    # Pattern looks for strings starting with src/, reports/, audit/, or similar, 
    # followed by word chars, dots, and slashes.
    pattern = r'(?:src|reports|audit|rubric|tools|nodes|tests)/[a-zA-Z0-9_\-\./]+'
    paths = re.findall(pattern, text)
    # Deduplicate and clean
    return sorted(list(set(paths)))


def check_concept_depth(text: str, concept: str) -> Tuple[bool, str]:
    """
    Assess if a concept is explained with depth or just mentioned as a buzzword.
    For the interim, we use a simple length/keyword-context heuristic.
    In the final implementation, this will be an LLM call.
    """
    concept_lower = concept.lower()
    text_lower = text.lower()
    
    if concept_lower not in text_lower:
        return False, "Concept not mentioned."

    # Simple heuristic: is there a significant amount of text around the first mention?
    start_idx = text_lower.find(concept_lower)
    context = text[max(0, start_idx - 100) : min(len(text), start_idx + 300)]
    
    # If the paragraph containing the concept is long and contains explanatory words
    explanatory_markers = ["because", "how", "implemented", "architecture", "resolved", "process"]
    depth_score = sum(1 for marker in explanatory_markers if marker in context.lower())
    
    is_deep = len(context) > 200 and depth_score >= 2
    
    return is_deep, context


def cross_reference_paths(report_paths: List[str], repo_path: str) -> Tuple[List[str], List[str]]:
    """
    Verifies reported file paths against actual repository structure.
    Returns (verified_paths, hallucinated_paths).
    """
    verified = []
    hallucinated = []
    
    root = Path(repo_path)
    for path_str in report_paths:
        full_path = root / path_str
        if full_path.exists():
            verified.append(path_str)
        else:
            hallucinated.append(path_str)
            
    return verified, hallucinated

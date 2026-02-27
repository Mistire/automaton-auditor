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


def extract_images_from_pdf(pdf_path: str) -> List[str]:
    """
    Extracts images from a PDF and saves them as temporary files.
    Returns a list of local file paths to the images.
    """
    if not pdf_path or not Path(pdf_path).exists():
        return []

    import tempfile
    import os
    
    image_paths = []
    try:
        doc = fitz.open(pdf_path)
        temp_dir = tempfile.mkdtemp(prefix="auditor_vision_")
        
        for i in range(len(doc)):
            page = doc[i]
            image_list = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                img_path = os.path.join(temp_dir, f"page{i+1}_img{img_index}.{image_ext}")
                with open(img_path, "wb") as f:
                    f.write(image_bytes)
                image_paths.append(img_path)
        
        doc.close()
    except Exception as e:
        print(f"Error extracting images: {e}")
        
    return image_paths


def cross_reference_paths(report_paths: List[str], repo_path: str) -> Tuple[List[str], List[str]]:
    """
    Verifies reported file paths against actual repository structure.
    Returns (verified_paths, hallucinated_paths).
    """
    verified = []
    hallucinated = []
    
    if not repo_path or not Path(repo_path).exists():
        return [], report_paths
        
    root = Path(repo_path)
    for path_str in report_paths:
        # Clean the path string (remove potential surrounding punctuation)
        clean_path = path_str.strip(".,;:()\"' ")
        if not clean_path:
            continue
            
        full_path = root / clean_path
        if full_path.exists():
            verified.append(clean_path)
        else:
            hallucinated.append(clean_path)
            
    return sorted(list(set(verified))), sorted(list(set(hallucinated)))

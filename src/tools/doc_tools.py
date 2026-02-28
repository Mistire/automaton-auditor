import re
import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Tuple
from src.state import Evidence
from src.tools.llm_tools import get_llm


try:
    from docling.document_converter import DocumentConverter
    HAS_DOCLING = True
except ImportError:
    HAS_DOCLING = False

def ingest_pdf(pdf_path: str) -> List[Dict[str, str]]:
    """
    Parses a PDF file using Docling (if available) or PyMuPDF as fallback.
    """
    if not pdf_path or not Path(pdf_path).exists():
        return []

    if HAS_DOCLING:
        try:
            converter = DocumentConverter()
            result = converter.convert(pdf_path)
            markdown_content = result.document.export_to_markdown()
            return [{"text": markdown_content, "metadata": {"source": str(pdf_path), "engine": "docling"}}]
        except Exception as e:
            print(f"Docling error: {e}. Falling back to PyMuPDF.")
    
    # Fallback to PyMuPDF
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return [{"text": text, "metadata": {"source": str(pdf_path), "engine": "fitz"}}]
    except Exception as e:
        print(f"Error parsing PDF with fitz: {e}")
        return []


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
    Forensic Protocol: Assess if a concept is explained with depth or just mentioned as a buzzword.
    Uses an LLM to distinguish between 'Keyword Dropping' and 'Substantive Explanation'.
    """
    concept_lower = concept.lower()
    text_lower = text.lower()
    
    # Find up to 3 mentions across the whole document
    import re
    mentions = [m.start() for m in re.finditer(re.escape(concept_lower), text_lower)][:3]
    if not mentions:
        return False, "Concept not mentioned."

    contexts = []
    for i, start_idx in enumerate(mentions):
        ctx = text[max(0, start_idx - 400) : min(len(text), start_idx + 800)]
        contexts.append(f"MENTION {i+1}:\n...{ctx.strip()}...")
    
    combined_context = "\n\n".join(contexts)
    
    prompt = f"""
    Evaluate if any of the following mentions provide a SUBSTANTIVE ARCHITECTURAL EXPLANATION of the concept '{concept}' within the system, 
    or if they are all just 'Keyword Dropping'.

    CONTEXT FROM REPORT:
    \"\"\"
    {combined_context}
    \"\"\"

    CRITERIA:
    - Substantive: Explains implementation logic, system flow (how A connects to B), or architectural rationale. Even a clear description of how the concept is realized in the code counts.
    - Keyword Dropping: Listed only in a feature list, mentioned as a buzzword, or used without explaining its role or implementation.

    RESPONSE FORMAT:
    Return only a JSON object: 
    {{"is_substantive": bool, "rationale": "one sentence summary"}}
    """
    
    try:
        llm = get_llm(temperature=0.0)
        # We use a simple JSON parser since we don't want to complicate this tool with Pydantic yet
        import json
        response = llm.invoke(prompt)
        # Basic cleanup of LLM response if it includes markdown blocks
        clean_content = response.content.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_content)
        
        return data.get("is_substantive", False), data.get("rationale", "No rationale provided.")
    except Exception as e:
        return False, f"LLM Depth Verification failed: {str(e)}"


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

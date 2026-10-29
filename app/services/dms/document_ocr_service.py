import os
import re
import logging
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def _extract_text_from_txt(file_path: str) -> Dict[str, Any]:
    """Extract text from plain text files."""
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                content = f.read()
            return {
                "extracted_text": content,
                "page_count": 1,
                "metadata_info": {"encoding": enc}
            }
        except UnicodeDecodeError:
            continue
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    return {
        "extracted_text": content,
        "page_count": 1,
        "metadata_info": {"encoding": "utf-8-replace"}
    }


def _extract_text_from_docx(file_path: str) -> Dict[str, Any]:
    """Extract text from docx file using standard library zipfile & XML."""
    try:
        # Try python-docx if installed
        import docx
        doc = docx.Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text]
        full_text = "\n".join(paragraphs)
        return {
            "extracted_text": full_text,
            "page_count": max(1, len(paragraphs) // 15),
            "metadata_info": {"extractor": "python-docx", "paragraphs": len(paragraphs)}
        }
    except Exception:
        pass

    # Built-in zero-dependency extraction for DOCX
    try:
        with zipfile.ZipFile(file_path) as z:
            xml_content = z.read("word/document.xml")
        tree = ET.fromstring(xml_content)
        # Namespace for wordprocessingML
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        texts = []
        for p in tree.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
            p_text = "".join(node.text for node in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t") if node.text)
            if p_text.strip():
                texts.append(p_text.strip())
        full_text = "\n".join(texts)
        return {
            "extracted_text": full_text,
            "page_count": max(1, len(texts) // 15),
            "metadata_info": {"extractor": "built-in-zip-xml", "paragraphs": len(texts)}
        }
    except Exception as e:
        logger.warning(f"Failed to extract docx text: {e}")
        return {
            "extracted_text": "",
            "page_count": 1,
            "error": f"DOCX parsing error: {str(e)}"
        }


def _extract_text_from_pdf(file_path: str) -> Dict[str, Any]:
    """Extract text from PDF using pypdf, fitz, or pdfplumber if available."""
    # 1. Try pypdf / PyPDF2
    try:
        import pypdf
        reader = pypdf.PdfReader(file_path)
        pages_text = []
        for page in reader.pages:
            t = page.extract_text() or ""
            pages_text.append(t)
        full_text = "\n--- Page Break ---\n".join(pages_text).strip()
        return {
            "extracted_text": full_text,
            "page_count": len(reader.pages),
            "metadata_info": {"extractor": "pypdf", "page_count": len(reader.pages)}
        }
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"pypdf extraction failed: {e}")

    # 2. Try fitz (PyMuPDF)
    try:
        import fitz
        doc = fitz.open(file_path)
        pages_text = [page.get_text() for page in doc]
        full_text = "\n--- Page Break ---\n".join(pages_text).strip()
        return {
            "extracted_text": full_text,
            "page_count": len(doc),
            "metadata_info": {"extractor": "pymupdf", "page_count": len(doc)}
        }
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"PyMuPDF extraction failed: {e}")

    # 3. Try pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            pages_text = [p.extract_text() or "" for p in pdf.pages]
            full_text = "\n--- Page Break ---\n".join(pages_text).strip()
            return {
                "extracted_text": full_text,
                "page_count": len(pdf.pages),
                "metadata_info": {"extractor": "pdfplumber", "page_count": len(pdf.pages)}
            }
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"pdfplumber extraction failed: {e}")

    # Fallback when no PDF parser installed
    return {
        "extracted_text": "[PDF file detected. To enable full PDF text extraction, install pypdf via 'pip install pypdf']",
        "page_count": 1,
        "metadata_info": {"extractor": "none", "note": "install pypdf to enable OCR for PDFs"}
    }


def _extract_text_from_image(file_path: str) -> Dict[str, Any]:
    """Extract text from images using pytesseract if available."""
    try:
        from PIL import Image
        import pytesseract
        img = Image.open(file_path)
        text = pytesseract.image_to_string(img)
        return {
            "extracted_text": text.strip(),
            "page_count": 1,
            "metadata_info": {"extractor": "pytesseract", "image_size": img.size}
        }
    except ImportError:
        return {
            "extracted_text": "[Image file detected. OCR engine (pytesseract/Pillow) is not installed.]",
            "page_count": 1,
            "metadata_info": {"extractor": "none", "note": "install pillow and pytesseract for image OCR"}
        }
    except Exception as e:
        logger.warning(f"Image OCR failed: {e}")
        return {
            "extracted_text": "",
            "page_count": 1,
            "error": f"Image OCR error: {str(e)}"
        }


def extract_document_content(file_path: str) -> Dict[str, Any]:
    """
    Extracts text, page count, and metadata from a document file.
    Supports txt, docx, pdf, images, and other formats.
    """
    if not os.path.exists(file_path):
        return {
            "extracted_text": "",
            "page_count": 0,
            "character_count": 0,
            "word_count": 0,
            "metadata_info": {},
            "error": f"File does not exist on disk: {file_path}"
        }

    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    text_extensions = {".txt", ".csv", ".json", ".md", ".log", ".xml", ".html", ".py", ".sql", ".yaml", ".yml"}
    image_extensions = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}

    res: Dict[str, Any] = {}
    if ext in text_extensions:
        res = _extract_text_from_txt(file_path)
    elif ext == ".docx":
        res = _extract_text_from_docx(file_path)
    elif ext == ".pdf":
        res = _extract_text_from_pdf(file_path)
    elif ext in image_extensions:
        res = _extract_text_from_image(file_path)
    else:
        # Binary or unsupported format
        res = {
            "extracted_text": f"[Binary file: unsupported format '{ext}']",
            "page_count": 1,
            "metadata_info": {"extension": ext}
        }

    text = res.get("extracted_text") or ""
    res["character_count"] = len(text)
    res["word_count"] = len(text.split())
    if "metadata_info" not in res:
        res["metadata_info"] = {}
    if "error" not in res:
        res["error"] = None
    return res


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[Dict[str, Any]]:
    """
    Splits text into chunks of roughly chunk_size characters with given overlap.
    Returns list of dicts with text, page_number, and chunk_index.
    """
    if not text:
        return []

    # Check for page markers
    page_splits = text.split("\n--- Page Break ---\n")
    chunks = []
    chunk_index = 0

    for page_idx, page_content in enumerate(page_splits, start=1):
        clean_page = page_content.strip()
        if not clean_page:
            continue

        step = max(1, chunk_size - overlap)
        for i in range(0, len(clean_page), step):
            c_text = clean_page[i : i + chunk_size].strip()
            if c_text:
                chunks.append({
                    "chunk_index": chunk_index,
                    "page_number": page_idx,
                    "text": c_text
                })
                chunk_index += 1

    return chunks

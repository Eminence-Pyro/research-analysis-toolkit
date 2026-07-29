"""
research_engine/writer/ocr_parser.py
Tier 2 — Scanned PDF support via Tesseract OCR

Many Nigerian university guidelines are scanned images, not text-layer
PDFs. This module adds OCR fallback to the guideline parser:

  1. Try pdfplumber/pypdf text extraction (existing behaviour)
  2. If extracted text is too short (<50 chars per page), fall back to OCR
  3. OCR converts PDF pages to images, then runs Tesseract on each page

Requirements:
    pip install pytesseract pdfplumber Pillow
    # Tesseract binary must also be installed:
    #   Ubuntu: sudo apt install tesseract-ocr
    #   macOS:  brew install tesseract
    #   Windows: https://github.com/UB-Mannheim/tesseract/wiki

Public API
----------
    extract_text_with_ocr(file_path)           → str
    is_scanned_pdf(file_path)                  → bool
    ocr_pdf(file_path, lang, dpi)              → str
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional


# ══════════════════════════════════════════════════════════════
# Scanned PDF detection
# ══════════════════════════════════════════════════════════════

def is_scanned_pdf(file_path: str | Path) -> bool:
    """
    Detect whether a PDF is scanned (image-only) or has a text layer.

    Heuristic: if pdfplumber extracts fewer than 50 characters per page
    on average, the PDF is likely scanned.
    """
    path = Path(file_path)
    if not path.exists() or path.suffix.lower() != ".pdf":
        return False

    try:
        import pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            total_chars = 0
            n_pages = len(pdf.pages)
            if n_pages == 0:
                return True
            for page in pdf.pages[:5]:  # sample first 5 pages
                text = page.extract_text() or ""
                total_chars += len(text.strip())
            avg = total_chars / min(n_pages, 5)
            return avg < 50
    except Exception:
        return True  # if we can't even open it with pdfplumber, try OCR


# ══════════════════════════════════════════════════════════════
# OCR extraction
# ══════════════════════════════════════════════════════════════

def ocr_pdf(
    file_path: str | Path,
    lang:      str = "eng",
    dpi:       int = 300,
) -> str:
    """
    Run Tesseract OCR on each page of a scanned PDF.

    Parameters
    ----------
    file_path : path to the scanned PDF
    lang      : Tesseract language code (default: "eng")
    dpi       : resolution for PDF→image conversion (300 is good for OCR)

    Returns
    -------
    str — the full extracted text
    """
    path = Path(file_path)

    # Check Tesseract is installed
    if not shutil.which("tesseract"):
        return (
            "[OCR failed: Tesseract is not installed. "
            "Install with: sudo apt install tesseract-ocr (Linux) "
            "or brew install tesseract (macOS)]"
        )

    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError:
        return (
            "[OCR failed: required packages not installed. "
            "Run: pip install pytesseract pdf2image Pillow]"
        )

    try:
        images = convert_from_path(str(path), dpi=dpi)
    except Exception as exc:
        return f"[OCR failed: could not convert PDF to images: {exc}]"

    pages_text = []
    for i, img in enumerate(images):
        try:
            text = pytesseract.image_to_string(img, lang=lang)
            pages_text.append(text)
        except Exception as exc:
            pages_text.append(f"[Page {i+1} OCR error: {exc}]")

    return "\n".join(pages_text)


# ══════════════════════════════════════════════════════════════
# Combined extraction (text layer + OCR fallback)
# ══════════════════════════════════════════════════════════════

def extract_text_with_ocr(file_path: str | Path) -> str:
    """
    Extract text from any file, with OCR fallback for scanned PDFs.

    Flow:
      1. .txt / .md → read directly
      2. .docx      → python-docx
      3. .pdf       → pdfplumber (text layer)
         └─ if text too short → Tesseract OCR fallback

    Returns the extracted text as a single string.
    """
    from research_engine.writer.guideline_parser import _extract_docx, _extract_pdf

    path   = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="replace")

    if suffix == ".docx":
        return _extract_docx(path)

    if suffix == ".pdf":
        # First try the normal text-layer extraction
        text = _extract_pdf(path)
        if len(text.strip()) > 200:
            return text

        # Text too short — likely scanned. Try OCR
        print(f"  📄 PDF appears to be scanned (only {len(text.strip())} chars extracted)")
        print(f"  🔄 Falling back to OCR…")
        ocr_text = ocr_pdf(path)
        if len(ocr_text.strip()) > 200:
            return ocr_text

        # Both methods failed
        return text or ocr_text

    raise ValueError(f"Unsupported file format: {suffix!r}")

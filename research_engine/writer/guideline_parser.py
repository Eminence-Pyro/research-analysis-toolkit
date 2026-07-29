"""
research_engine/writer/guideline_parser.py

Extracts structured ProjectMetadata from uploaded documents.

Supports:
  - .docx  (Word documents)
  - .pdf   (text-layer PDFs — scanned PDFs not supported)
  - .txt   (plain text)
  - .md    (markdown)

The parser uses regex + keyword heuristics first (fast, no API cost).
The AI enrichment step (LLM-based extraction) is called separately
by the app layer when heuristics are insufficient.

Public API
----------
    extract_text(file_path)                   → str
    parse_guideline(text)                     → ProjectMetadata
    extract_objectives(text)                  → list[str]
    extract_research_questions(text)          → list[str]
    extract_hypotheses(text)                  → list[str]
"""
from __future__ import annotations

import re
from pathlib import Path

from research_engine.writer.project_session import (
    ProjectMetadata, EducationLevel, ResearchDesign
)


# ══════════════════════════════════════════════════════════════
# Text extraction
# ══════════════════════════════════════════════════════════════

def extract_text(file_path: str | Path) -> str:
    """
    Extract raw text from a supported file format.

    Automatically falls back to OCR for scanned PDFs.

    Parameters
    ----------
    file_path : path to .docx, .pdf, .txt, or .md file

    Returns
    -------
    str — the full extracted text, or empty string on failure
    """
    from research_engine.writer.ocr_parser import extract_text_with_ocr
    return extract_text_with_ocr(file_path)


def _extract_docx(path: Path) -> str:
    try:
        from docx import Document
        doc  = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as exc:
        return f"[DOCX extraction failed: {exc}]"


def _extract_pdf(path: Path) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return "\n".join(pages)
    except ImportError:
        # Fallback: pypdf
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            return "\n".join(
                page.extract_text() or "" for page in reader.pages
            )
        except ImportError:
            return (
                "[PDF extraction requires pdfplumber or pypdf. "
                "Install with: pip install pdfplumber]"
            )
    except Exception as exc:
        return f"[PDF extraction failed: {exc}]"


# ══════════════════════════════════════════════════════════════
# Metadata extraction (regex/heuristics)
# ══════════════════════════════════════════════════════════════

def parse_guideline(text: str) -> ProjectMetadata:
    """
    Extract ProjectMetadata from raw guideline text using heuristics.
    Fields that cannot be extracted are left at their defaults.

    Parameters
    ----------
    text : full text of the guideline document

    Returns
    -------
    ProjectMetadata
    """
    meta = ProjectMetadata()

    meta.title              = _extract_title(text)
    meta.level              = _extract_level(text)
    meta.institution        = _extract_institution(text)
    meta.department         = _extract_department(text)
    meta.year               = _extract_year(text)
    meta.citation_style     = _extract_citation_style(text)
    meta.research_design    = _extract_research_design(text)
    meta.population         = _extract_population(text)
    meta.study_area         = _extract_study_area(text)
    meta.word_count_target  = _extract_word_count(text)
    meta.objectives         = extract_objectives(text)
    meta.research_questions = extract_research_questions(text)
    meta.hypotheses         = extract_hypotheses(text)
    meta.keywords           = _extract_keywords(text)

    return meta


# ── Heuristic helpers ─────────────────────────────────────────

def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _extract_title(text: str) -> str:
    # Look for "Title:", "Project Title:", "Research Topic:"
    patterns = [
        r"(?:project\s+title|research\s+title|title\s+of\s+(?:the\s+)?(?:project|study|research))[:\s]+([^\n]{10,120})",
        r"(?:^|\n)title[:\s]+([^\n]{10,120})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return _clean(m.group(1))
    # Fallback: first non-empty line that looks like a title (≥5 words, Title Case)
    for line in text.split("\n")[:15]:
        line = line.strip()
        words = line.split()
        if 5 <= len(words) <= 20 and sum(1 for w in words if w[:1].isupper()) > len(words) // 2:
            return _clean(line)
    return ""


def _extract_level(text: str) -> EducationLevel:
    text_l = text.lower()
    for phrase, level in [
        (["phd", "doctorate", "doctoral"], EducationLevel.PHD),
        (["m.sc", "msc", "master of science", "master of arts", "m.a.", "postgraduate"], EducationLevel.MSC),
        (["pgd", "postgraduate diploma"], EducationLevel.PGD),
        (["hnd", "higher national diploma"], EducationLevel.HND),
        (["ond", "ordinary national diploma"], EducationLevel.OND),
        (["b.sc", "bsc", "bachelor", "undergraduate", "degree project", "final year project"], EducationLevel.BSC),
    ]:
        if any(p in text_l for p in phrase):
            return level
    return EducationLevel.UNKNOWN


def _extract_institution(text: str) -> str:
    patterns = [
        r"(?:university|college|polytechnic|institute)\s+of\s+[A-Z][A-Za-z\s,]+",
        r"(?:institution|university|college)[:\s]+([^\n]{5,80})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return _clean(m.group())
    return ""


def _extract_department(text: str) -> str:
    m = re.search(
        r"(?:department|dept\.?)\s+of\s+([A-Za-z\s&,/]+?)(?:\n|\.|\,|and\s)",
        text, re.IGNORECASE
    )
    return _clean(m.group()) if m else ""


def _extract_year(text: str) -> str:
    m = re.search(r"\b(20[0-9]{2})[/\-]?(20[0-9]{2})?\b", text)
    if m:
        return m.group(0)
    return ""


def _extract_citation_style(text: str) -> str:
    text_l = text.lower()
    if "vancouver" in text_l:   return "Vancouver"
    if "harvard"   in text_l:   return "Harvard"
    if "chicago"   in text_l:   return "Chicago"
    if "apa"       in text_l:   return "APA"
    return "APA"  # default for health sciences


def _extract_research_design(text: str) -> ResearchDesign:
    text_l = text.lower()
    mappings = [
        (["cross-sectional", "cross sectional"],     ResearchDesign.CROSS_SECTIONAL),
        (["quasi-experimental", "quasi experimental"],ResearchDesign.QUASI_EXPERIMENTAL),
        (["experimental"],                            ResearchDesign.EXPERIMENTAL),
        (["correlational"],                           ResearchDesign.CORRELATIONAL),
        (["longitudinal"],                            ResearchDesign.LONGITUDINAL),
        (["case study"],                              ResearchDesign.CASE_STUDY),
        (["mixed method"],                            ResearchDesign.MIXED_METHODS),
        (["descriptive"],                             ResearchDesign.DESCRIPTIVE),
    ]
    for phrases, design in mappings:
        if any(p in text_l for p in phrases):
            return design
    return ResearchDesign.UNKNOWN


def _extract_population(text: str) -> str:
    m = re.search(
        r"(?:study\s+population|target\s+population|population\s+of\s+(?:the\s+)?study)[:\s]+([^\n.]{10,120})",
        text, re.IGNORECASE
    )
    return _clean(m.group(1)) if m else ""


def _extract_study_area(text: str) -> str:
    m = re.search(
        r"(?:study\s+area|area\s+of\s+study|conducted\s+(?:at|in))[:\s]+([^\n.]{5,80})",
        text, re.IGNORECASE
    )
    return _clean(m.group(1)) if m else ""


def _extract_word_count(text: str) -> int:
    patterns = [
        r"(\d[,\d]*)\s*words?(?:\s+(?:per|for|each)\s+chapter)?",
        r"total\s+word\s+count[:\s]+(\d[,\d]*)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return int(m.group(1).replace(",", ""))
    return 0


def _extract_keywords(text: str) -> list[str]:
    m = re.search(
        r"key\s*words?[:\s]+([^\n]{5,200})",
        text, re.IGNORECASE
    )
    if m:
        raw = m.group(1)
        return [_clean(k) for k in re.split(r"[;,]", raw) if k.strip()]
    return []


# ── Structured list extraction ────────────────────────────────

def _extract_numbered_list(text: str, section_header: str) -> list[str]:
    """
    Extract a numbered list that appears after a section header.
    e.g. "Objectives of the Study\n1. To determine...\n2. To assess..."
    """
    # Find section
    pattern = rf"(?:{section_header})[:\s]*\n((?:\s*\d+[\.\)]\s*.+\n?)+)"
    m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    if not m:
        return []
    block = m.group(1)
    items = re.findall(r"\d+[\.\)]\s*(.+)", block)
    return [_clean(i) for i in items if i.strip()]


def extract_objectives(text: str) -> list[str]:
    """Extract research objectives from guideline text."""
    headers = r"(?:objectives?(?:\s+of\s+(?:the\s+)?(?:study|research))?|specific\s+objectives?)"
    result  = _extract_numbered_list(text, headers)
    if result:
        return result
    # Fallback: "To + verb" pattern
    items = re.findall(r"(?:^|\n)\s*(?:\d+[\.\)]|\-|\•)?\s*(To\s+[a-z][^.\n]{10,120})", text)
    return [_clean(i) for i in items[:8] if i]


def extract_research_questions(text: str) -> list[str]:
    """Extract research questions from guideline text."""
    headers = r"research\s+questions?"
    result  = _extract_numbered_list(text, headers)
    if result:
        return result
    # Fallback: lines ending in "?"
    questions = re.findall(
        r"(?:^|\n)\s*(?:\d+[\.\)]|\-|\•)?\s*([A-Z][^?\n]{10,120}\?)",
        text
    )
    return [_clean(q) for q in questions[:6] if q]


def extract_hypotheses(text: str) -> list[str]:
    """Extract hypotheses (H0 / H1) from guideline text."""
    headers = r"(?:hypothes[ei]s|null\s+hypothes[ei]s|research\s+hypothes[ei]s)"
    result  = _extract_numbered_list(text, headers)
    if result:
        return result
    # Fallback: H0/H1 patterns
    items = re.findall(
        r"(?:H[0O][\d]?|H[1I][\d]?|Null hypothesis|Alternative hypothesis)[:\s]+([^\n]{10,150})",
        text, re.IGNORECASE
    )
    return [_clean(i) for i in items[:8] if i]

"""
research_engine/exporters/pdf_exporter.py
Tier 2 — PDF export via reportlab

Produces a submission-ready PDF with:
  - Title page (cover page)
  - Abstract
  - All chapters with proper heading hierarchy
  - Reference list
  - Page numbers (footer)
  - Academic formatting (Times New Roman, 1.5 line spacing)

Public API
----------
    export_project_pdf(session, output_path, reference_list=None) → Path
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import re

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
        KeepTogether
    )
    from reportlab.lib.colors import HexColor, black, white
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


# ── Styles ────────────────────────────────────────────────────

def _build_styles():
    """Build the paragraph styles for the PDF."""
    ss = getSampleStyleSheet()

    styles = {
        "title_page_title": ParagraphStyle(
            "TitlePageTitle", parent=ss["Title"],
            fontName="Times-Bold", fontSize=14, alignment=TA_CENTER,
            spaceBefore=60, spaceAfter=20, leading=18
        ),
        "title_page_sub": ParagraphStyle(
            "TitlePageSub", parent=ss["Normal"],
            fontName="Times-Roman", fontSize=11, alignment=TA_CENTER,
            spaceBefore=8, spaceAfter=8, leading=14
        ),
        "title_page_meta": ParagraphStyle(
            "TitlePageMeta", parent=ss["Normal"],
            fontName="Times-Roman", fontSize=12, alignment=TA_CENTER,
            spaceBefore=6, spaceAfter=6
        ),
        "heading1": ParagraphStyle(
            "Heading1", parent=ss["Heading1"],
            fontName="Times-Bold", fontSize=16, alignment=TA_CENTER,
            spaceBefore=24, spaceAfter=12, leading=20
        ),
        "heading2": ParagraphStyle(
            "Heading2", parent=ss["Heading2"],
            fontName="Times-Bold", fontSize=13, alignment=TA_LEFT,
            spaceBefore=16, spaceAfter=8, leading=16
        ),
        "heading3": ParagraphStyle(
            "Heading3", parent=ss["Heading3"],
            fontName="Times-Bold", fontSize=12, alignment=TA_LEFT,
            spaceBefore=12, spaceAfter=6, leading=15
        ),
        "body": ParagraphStyle(
            "Body", parent=ss["Normal"],
            fontName="Times-Roman", fontSize=12, alignment=TA_JUSTIFY,
            leading=18,  # 1.5 line spacing for 12pt
            firstLineIndent=18, spaceAfter=6
        ),
        "body_first": ParagraphStyle(
            "BodyFirst", parent=ss["Normal"],
            fontName="Times-Roman", fontSize=12, alignment=TA_JUSTIFY,
            leading=18, spaceAfter=6
            # no firstLineIndent for first paragraph after heading
        ),
        "ref_heading": ParagraphStyle(
            "RefHeading", parent=ss["Heading1"],
            fontName="Times-Bold", fontSize=14, alignment=TA_CENTER,
            spaceBefore=24, spaceAfter=12
        ),
        "ref_entry": ParagraphStyle(
            "RefEntry", parent=ss["Normal"],
            fontName="Times-Roman", fontSize=11, alignment=TA_JUSTIFY,
            leading=15, leftIndent=18, firstLineIndent=-18,
            spaceAfter=6
        ),
        "abstract_body": ParagraphStyle(
            "AbstractBody", parent=ss["Normal"],
            fontName="Times-Roman", fontSize=11, alignment=TA_JUSTIFY,
            leading=16, spaceAfter=6
        ),
    }
    return styles


# ── Page number callback ──────────────────────────────────────

def _add_page_number(canvas, doc):
    """Add page number at the bottom center of each page."""
    canvas.saveState()
    canvas.setFont("Times-Roman", 10)
    page_num = canvas.getPageNumber()
    canvas.drawCentredString(
        A4[0] / 2, 1.5 * cm,
        str(page_num)
    )
    canvas.restoreState()


# ── Markdown to reportlab parser ──────────────────────────────

def _parse_markdown_to_flowables(text: str, styles: dict) -> list:
    """Parse markdown-ish chapter content into reportlab flowables."""
    flowables = []
    first_para = True

    for line in text.split("\n"):
        s = line.strip()
        if not s:
            first_para = True
            continue

        if s.startswith("#### "):
            # Use heading3 for level-4 headings
            flowables.append(Paragraph(s[5:], styles["heading3"]))
            first_para = True
        elif s.startswith("### "):
            flowables.append(Paragraph(s[4:], styles["heading3"]))
            first_para = True
        elif s.startswith("## "):
            flowables.append(Paragraph(s[3:], styles["heading2"]))
            first_para = True
        elif s.startswith("# "):
            flowables.append(Paragraph(s[2:], styles["heading1"]))
            first_para = True
        else:
            # Escape HTML chars that reportlab doesn't handle
            s_escaped = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            style = styles["body_first"] if first_para else styles["body"]
            flowables.append(Paragraph(s_escaped, style))
            first_para = False

    return flowables


# ══════════════════════════════════════════════════════════════
# Main export function
# ══════════════════════════════════════════════════════════════

def export_project_pdf(
    session,
    output_path:    str | Path,
    reference_list=None,
) -> Path:
    """
    Export the full project to a submission-ready PDF document.

    Parameters
    ----------
    session        : ProjectSession with chapters written
    output_path    : where to save the .pdf file
    reference_list : optional ReferenceList from reference_generator

    Returns
    -------
    Path — saved .pdf file
    """
    if not PDF_AVAILABLE:
        raise ImportError(
            "reportlab required: pip install reportlab"
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    m = session.metadata
    styles = _build_styles()

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        topMargin=2.54 * cm,
        bottomMargin=2.54 * cm,
        leftMargin=3.0 * cm,   # binding margin
        rightMargin=2.54 * cm,
        title=m.title or "Research Project",
        author=m.student_name or "Research Analysis Toolkit",
    )

    story = []

    # ── 1. Title page ──────────────────────────────────────────
    if m.institution:
        story.append(Paragraph(m.institution.upper(), styles["title_page_title"]))
    if m.department:
        story.append(Paragraph(m.department, styles["title_page_sub"]))
    story.append(Spacer(1, 40))

    if m.title:
        story.append(Paragraph(m.title.upper(), styles["title_page_title"]))
    story.append(Spacer(1, 30))

    story.append(Paragraph(
        "A Research Project Submitted in Partial Fulfilment of the Requirements",
        styles["title_page_sub"]
    ))
    level_name = m.level.value.upper() if m.level else "B.Sc"
    story.append(Paragraph(
        f"for the Award of {level_name} Degree",
        styles["title_page_sub"]
    ))

    story.append(Spacer(1, 50))
    if m.student_name:
        story.append(Paragraph("By", styles["title_page_sub"]))
        story.append(Paragraph(m.student_name.upper(), styles["title_page_meta"]))

    story.append(Spacer(1, 40))
    year = m.year or str(datetime.now().year)
    story.append(Paragraph(year, styles["title_page_meta"]))
    story.append(PageBreak())

    # ── 2. Abstract ────────────────────────────────────────────
    ch1 = session.chapters.get(1)
    ch5 = session.chapters.get(5)
    story.append(Paragraph("ABSTRACT", styles["heading1"]))
    if ch1 and ch5:
        bg_words = ch1.content.split()[:150]
        conc_words = ch5.content.split()[-80:]
        abstract = " ".join(bg_words) + " ... " + " ".join(conc_words)
        story.append(Paragraph(abstract[:800], styles["abstract_body"]))
    else:
        story.append(Paragraph(
            "[Abstract — 150–250 words summarising background, objectives, "
            "methods, findings, and conclusions.]",
            styles["abstract_body"]
        ))
    if m.keywords:
        story.append(Spacer(1, 12))
        story.append(Paragraph(
            f"<b>Keywords:</b> {', '.join(m.keywords)}",
            styles["abstract_body"]
        ))
    story.append(PageBreak())

    # ── 3. Chapters ────────────────────────────────────────────
    for n in sorted(session.chapters.keys()):
        ch = session.chapters[n]
        story.extend(_parse_markdown_to_flowables(ch.content, styles))
        story.append(PageBreak())

    # ── 4. Reference list ───────────────────────────────────────
    story.append(Paragraph("REFERENCES", styles["ref_heading"]))
    if reference_list and reference_list.entries:
        for entry in sorted(reference_list.entries, key=lambda e: e.author.lower()):
            text_escaped = entry.full_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(text_escaped, styles["ref_entry"]))
    else:
        story.append(Paragraph(
            "[References will be auto-generated. Run the reference generator first.]",
            styles["abstract_body"]
        ))

    # ── Build PDF ──────────────────────────────────────────────
    doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)

    return output_path

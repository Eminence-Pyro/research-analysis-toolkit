"""
research_engine/writer/citation_diversity.py
Tier 2 — Plagiarism-safe citation diversity scoring

Scans generated chapter text for citation patterns and flags:
  - Over-reliance on a single author (>30% of all citations)
  - Insufficient citation density (<1 citation per 200 words)
  - Repeated use of the same source within a single section
  - Missing citations in sections that should be heavily cited (Ch 2, Ch 4)

Public API
----------
    score_citation_diversity(text)              → CitationDiversityReport
    score_session(session)                      → dict[int, CitationDiversityReport]
    suggest_improvements(report)                → list[str]
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CitationDiversityReport:
    """Citation analysis for a single chapter or text block."""
    total_citations:       int = 0
    unique_authors:         int = 0
    word_count:             int = 0
    citations_per_200:      float = 0.0
    max_author_share:      float = 0.0
    dominant_author:       str   = ""
    author_counts:         dict[str, int] = field(default_factory=dict)
    repeated_in_sections:  list[str] = field(default_factory=list)
    issues:                list[str] = field(default_factory=list)
    score:                 float = 0.0  # 0–100
    grade:                 str   = "—"

    def summary(self) -> str:
        lines = [
            f"Citations: {self.total_citations} | Unique authors: {self.unique_authors}",
            f"Per 200 words: {self.citations_per_200:.2f}",
            f"Dominant author: {self.dominant_author} ({self.max_author_share*100:.0f}% share)",
            f"Score: {self.score:.0f}/100 ({self.grade})",
        ]
        if self.issues:
            lines.append("Issues:")
            for issue in self.issues:
                lines.append(f"  ⚠  {issue}")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# Citation extraction (reuse from reference_generator)
# ══════════════════════════════════════════════════════════════

_PARENTHETICAL = re.compile(
    r'\(([A-Z][A-Za-z\-]+(?:\s+(?:&|and)\s+[A-Z][A-Za-z\-]+|'
    r'\s+et\s+al\.)?),?\s+((?:19|20)\d{2}(?:,\s*p\.?\s*\d+)?)\)',
    re.UNICODE
)
_NARRATIVE = re.compile(
    r'([A-Z][A-Za-z\-]+(?:\s+(?:and|&)\s+[A-Z][A-Za-z\-]+|'
    r'\s+et\s+al\.)?)\s+\(((?:19|20)\d{2}(?:,\s*p\.?\s*\d+)?)\)',
    re.UNICODE
)


def _extract_author_names(text: str) -> list[str]:
    """Extract just the author surnames from all citations in text."""
    authors = []
    for m in _PARENTHETICAL.finditer(text):
        authors.append(m.group(1).strip())
    for m in _NARRATIVE.finditer(text):
        authors.append(m.group(1).strip())
    return authors


# ══════════════════════════════════════════════════════════════
# Section detection (find ## headings)
# ══════════════════════════════════════════════════════════════

def _split_by_sections(text: str) -> dict[str, str]:
    """Split chapter text into sections by ## headings."""
    sections = {}
    current_heading = "_intro"
    current_lines = []
    for line in text.split("\n"):
        if line.strip().startswith("## "):
            if current_lines:
                sections[current_heading] = "\n".join(current_lines)
            current_heading = line.strip()[3:]
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections[current_heading] = "\n".join(current_lines)
    return sections


# ══════════════════════════════════════════════════════════════
# Main scoring function
# ══════════════════════════════════════════════════════════════

def score_citation_diversity(text: str) -> CitationDiversityReport:
    """
    Analyze citation patterns in a text block and return a diversity report.

    Checks:
    - Citation density (citations per 200 words)
    - Author diversity (no single author >30% of all citations)
    - Repeated citations within sections (same author 3+ times in one section)
    """
    report = CitationDiversityReport()

    words = text.split()
    report.word_count = len(words)

    authors = _extract_author_names(text)
    report.total_citations = len(authors)

    if report.total_citations == 0:
        report.issues.append("No citations found in this text.")
        report.score = 0
        report.grade = "F"
        return report

    counter = Counter(authors)
    report.author_counts = dict(counter.most_common())
    report.unique_authors = len(counter)
    report.citations_per_200 = (report.total_citations / max(report.word_count, 1)) * 200

    # Most dominant author
    top_author, top_count = counter.most_common(1)[0]
    report.dominant_author = top_author
    report.max_author_share = top_count / report.total_citations

    # ── Issue checks ───────────────────────────────────────────
    # 1. Citation density
    if report.citations_per_200 < 1.0:
        report.issues.append(
            f"Low citation density: {report.citations_per_200:.2f} per 200 words "
            f"(target: ≥1.0 for Ch 2/4)"
        )

    # 2. Single-author dominance
    if report.max_author_share > 0.30:
        report.issues.append(
            f"Over-reliance on '{top_author}': "
            f"{report.max_author_share*100:.0f}% of all citations "
            f"(target: <30%)"
        )

    # 3. Repeated citations within sections
    sections = _split_by_sections(text)
    for heading, sec_text in sections.items():
        sec_authors = _extract_author_names(sec_text)
        sec_counter = Counter(sec_authors)
        for author, count in sec_counter.items():
            if count >= 3:
                report.repeated_in_sections.append(
                    f"'{author}' cited {count}x in section '{heading[:40]}'"
                )

    if len(report.repeated_in_sections) > 2:
        report.issues.append(
            f"Repeated citations: {len(report.repeated_in_sections)} instances of "
            f"same author 3+ times in one section"
        )

    # 4. No citations at all in a long section
    for heading, sec_text in sections.items():
        sec_words = len(sec_text.split())
        sec_cites = len(_extract_author_names(sec_text))
        if sec_words > 200 and sec_cites == 0:
            heading_l = heading.lower()
            if any(kw in heading_l for kw in ["review", "literature", "framework", "empirical"]):
                report.issues.append(
                    f"Section '{heading[:40]}' has {sec_words} words but 0 citations"
                )

    # ── Score calculation ──────────────────────────────────────
    score = 100
    if report.citations_per_200 < 1.0:
        score -= 20
    if report.citations_per_200 < 0.5:
        score -= 15
    if report.max_author_share > 0.30:
        score -= 15
    if report.max_author_share > 0.50:
        score -= 10
    if len(report.repeated_in_sections) > 2:
        score -= 10
    score -= min(len(report.issues) * 3, 20)

    report.score = max(score, 0)
    if report.score >= 85: report.grade = "A"
    elif report.score >= 70: report.grade = "B"
    elif report.score >= 55: report.grade = "C"
    elif report.score >= 40: report.grade = "D"
    else: report.grade = "F"

    return report


# ══════════════════════════════════════════════════════════════
# Session-level scoring
# ══════════════════════════════════════════════════════════════

def score_session(session) -> dict[int, CitationDiversityReport]:
    """
    Score citation diversity for all chapters in a session.

    Returns a dict of {chapter_number: CitationDiversityReport}.
    """
    reports = {}
    for n, ch in session.chapters.items():
        reports[n] = score_citation_diversity(ch.content)
    return reports


# ══════════════════════════════════════════════════════════════
# Improvement suggestions
# ══════════════════════════════════════════════════════════════

def suggest_improvements(report: CitationDiversityReport) -> list[str]:
    """
    Generate human-readable improvement suggestions based on the report.
    """
    suggestions = []
    if report.total_citations == 0:
        suggestions.append("Add in-text citations — this section currently has none.")
        return suggestions

    if report.citations_per_200 < 1.0:
        suggestions.append(
            f"Add more citations (currently {report.citations_per_200:.2f}/200 words, "
            f"target ≥1.0). Insert 1–2 more sources per paragraph."
        )

    if report.max_author_share > 0.30:
        suggestions.append(
            f"Diversify your sources — '{report.dominant_author}' accounts for "
            f"{report.max_author_share*100:.0f}% of citations. Find 2–3 additional "
            f"authors who discuss similar topics."
        )

    if report.repeated_in_sections:
        suggestions.append(
            f"Reduce repetition — the same author is cited 3+ times in "
            f"{len(report.repeated_in_sections)} section(s). Combine references "
            f"or introduce alternative viewpoints."
        )

    for issue in report.issues:
        if "0 citations" in issue:
            suggestions.append(f"Add citations to uncited sections: {issue}")

    if not suggestions:
        suggestions.append("Citation diversity looks good — no changes needed.")

    return suggestions

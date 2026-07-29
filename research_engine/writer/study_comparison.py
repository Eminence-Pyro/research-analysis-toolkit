"""
research_engine/writer/study_comparison.py
Tier 3 — Multi-study comparison

Compare two project sessions side-by-side. Useful when:
  - A student is building on a previous study
  - Doing a replication study
  - Comparing findings across two studies

Public API
----------
    compare_sessions(session_a, session_b)  → ComparisonReport
    render_comparison_table(report)         → str (markdown table)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChapterComparison:
    chapter:         int
    title:           str
    a_word_count:    int = 0
    b_word_count:    int = 0
    a_exists:        bool = False
    b_exists:        bool = False
    shared_keywords: list[str] = field(default_factory=list)
    a_only_keywords: list[str] = field(default_factory=list)
    b_only_keywords: list[str] = field(default_factory=list)


@dataclass
class ComparisonReport:
    """Side-by-side comparison of two project sessions."""
    session_a_id:          str = ""
    session_b_id:          str = ""
    a_title:               str = ""
    b_title:               str = ""
    a_level:               str = ""
    b_level:               str = ""
    a_chapters_done:       int  = 0
    b_chapters_done:       int  = 0
    a_total_words:         int  = 0
    b_total_words:         int  = 0
    chapter_comparisons:   list[ChapterComparison] = field(default_factory=list)
    shared_objectives:     list[str] = field(default_factory=list)
    shared_keywords:       list[str] = field(default_factory=list)
    differences:           list[str] = field(default_factory=list)
    similarity_note:       str  = ""

    def to_text(self) -> str:
        lines = [
            "=" * 60,
            "STUDY COMPARISON REPORT",
            "=" * 60,
            f"\nStudy A: {self.a_title} ({self.a_level.upper()}) — {self.a_chapters_done}/5 chapters, ~{self.a_total_words:,} words",
            f"Study B: {self.b_title} ({self.b_level.upper()}) — {self.b_chapters_done}/5 chapters, ~{self.b_total_words:,} words",
        ]

        if self.chapter_comparisons:
            lines.append("\n" + "-" * 60)
            lines.append("CHAPTER-BY-CHAPTER COMPARISON")
            lines.append("-" * 60)
            for cc in self.chapter_comparisons:
                lines.append(f"\n  Chapter {cc.chapter}: {cc.title}")
                lines.append(f"    A: {'✅' if cc.a_exists else '❌'} {cc.a_word_count:,} words | "
                             f"B: {'✅' if cc.b_exists else '❌'} {cc.b_word_count:,} words")
                if cc.shared_keywords:
                    lines.append(f"    Shared keywords: {', '.join(cc.shared_keywords[:8])}")

        if self.shared_objectives:
            lines.append(f"\n  Shared objectives: {', '.join(self.shared_objectives[:5])}")

        if self.differences:
            lines.append("\n  Differences:")
            for d in self.differences:
                lines.append(f"    • {d}")

        if self.similarity_note:
            lines.append(f"\n  Assessment: {self.similarity_note}")

        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# Keyword extraction (simple but effective)
# ══════════════════════════════════════════════════════════════

from collections import Counter
import re

_STOP_WORDS = set(
    "the a an and or but in on at to for of is are was were be been being "
    "this that these those it its as with from by have has had do does did "
    "will would could should may might can must not no yes if then than "
    "also more most very just so such only own same other some any all each "
    "few many much such which who whom whose what where when why how into "
    "through during before after above below up down out off over under "
    "again further once here there both each few more most other some such "
    "about above above across after against along among around at before "
    "behind beside between beyond but by concerning considering despite "
    "except for from in inside into like near of off on onto outside over "
    "past regarding round since through throughout till to toward towards "
    "under underneath until up upon with within without study research data "
    "analysis results findings chapter section table figure respondents "
    "study population sample significance hypothesis null rejected accepted".split()
)


def _extract_keywords(text: str, top_n: int = 15) -> list[str]:
    """Extract the most meaningful keywords from text."""
    words = re.findall(r'[a-zA-Z]{4,}', text.lower())
    meaningful = [w for w in words if w not in _STOP_WORDS]
    counter = Counter(meaningful)
    return [w for w, _ in counter.most_common(top_n)]


# ══════════════════════════════════════════════════════════════
# Main comparison function
# ══════════════════════════════════════════════════════════════

def compare_sessions(
    session_a,
    session_b,
) -> ComparisonReport:
    """
    Compare two ProjectSession objects side-by-side.
    """
    from research_engine.writer.project_session import CHAPTER_TITLES

    report = ComparisonReport()
    ma, mb = session_a.metadata, session_b.metadata

    report.session_a_id    = session_a.session_id
    report.session_b_id    = session_b.session_id
    report.a_title         = ma.title or "(Untitled)"
    report.b_title         = mb.title or "(Untitled)"
    report.a_level         = ma.level.value if ma.level else "unknown"
    report.b_level         = mb.level.value if mb.level else "unknown"
    report.a_chapters_done = len(session_a.chapters_done)
    report.b_chapters_done = len(session_b.chapters_done)
    report.a_total_words   = sum(ch.word_count for ch in session_a.chapters.values())
    report.b_total_words   = sum(ch.word_count for ch in session_b.chapters.values())

    # Shared objectives
    a_obj = set(o.lower().strip() for o in (ma.objectives or []))
    b_obj = set(o.lower().strip() for o in (mb.objectives or []))
    report.shared_objectives = list(a_obj & b_obj)

    # Chapter-by-chapter comparison
    for n in range(1, 6):
        title = CHAPTER_TITLES.get(n, f"Chapter {n}")
        ca = session_a.get_chapter(n)
        cb = session_b.get_chapter(n)

        cc = ChapterComparison(
            chapter=n, title=title,
            a_exists=ca is not None, b_exists=cb is not None,
            a_word_count=ca.word_count if ca else 0,
            b_word_count=cb.word_count if cb else 0,
        )

        if ca and cb:
            ka = set(_extract_keywords(ca.content))
            kb = set(_extract_keywords(cb.content))
            cc.shared_keywords = sorted(ka & kb)
            cc.a_only_keywords  = sorted(ka - kb)
            cc.b_only_keywords  = sorted(kb - ka)

        report.chapter_comparisons.append(cc)

    # Global shared keywords
    all_a_text = " ".join(ch.content for ch in session_a.chapters.values())
    all_b_text = " ".join(ch.content for ch in session_b.chapters.values())
    ka_all = set(_extract_keywords(all_a_text, top_n=20))
    kb_all = set(_extract_keywords(all_b_text, top_n=20))
    report.shared_keywords = sorted(ka_all & kb_all)

    # Differences
    if ma.level != mb.level:
        report.differences.append(f"Different academic levels: {ma.level.value} vs {mb.level.value}")
    if ma.research_design != mb.research_design:
        report.differences.append(
            f"Different research designs: {ma.research_design.value} vs {mb.research_design.value}"
        )
    if ma.citation_style != mb.citation_style:
        report.differences.append(
            f"Different citation styles: {ma.citation_style} vs {mb.citation_style}"
        )
    if ma.population != mb.population:
        report.differences.append(
            f"Different populations: {ma.population or 'N/A'} vs {mb.population or 'N/A'}"
        )

    # Similarity assessment
    if report.shared_objectives:
        report.similarity_note = (
            f"Studies share {len(report.shared_objectives)} common objectives. "
            f"This appears to be a related or replication study."
        )
    elif len(report.shared_keywords) > 8:
        report.similarity_note = (
            f"Studies share {len(report.shared_keywords)} common keywords but different objectives. "
            f"Same research area, different focus."
        )
    else:
        report.similarity_note = "Studies appear to be on different topics."

    return report


def render_comparison_table(report: ComparisonReport) -> str:
    """Render the comparison as a markdown table."""
    lines = [
        "| Aspect | Study A | Study B |",
        "|--------|----------|----------|",
        f"| Title | {report.a_title} | {report.b_title} |",
        f"| Level | {report.a_level.upper()} | {report.b_level.upper()} |",
        f"| Chapters | {report.a_chapters_done}/5 | {report.b_chapters_done}/5 |",
        f"| Total Words | ~{report.a_total_words:,} | ~{report.b_total_words:,} |",
        f"| Shared Keywords | {', '.join(report.shared_keywords[:8])} | |",
    ]
    for cc in report.chapter_comparisons:
        a_stat = f"✅ {cc.a_word_count:,}w" if cc.a_exists else "❌"
        b_stat = f"✅ {cc.b_word_count:,}w" if cc.b_exists else "❌"
        lines.append(f"| Ch{cc.chapter}: {cc.title[:25]} | {a_stat} | {b_stat} |")
    return "\n".join(lines)

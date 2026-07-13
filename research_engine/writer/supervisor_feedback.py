"""
research_engine/writer/supervisor_feedback.py
Tier 2 — Supervisor feedback loop

Accepts supervisor comments as free text or an uploaded file,
maps each comment to the relevant chapter(s), and triggers
targeted revisions automatically.

Public API
----------
    parse_feedback(text)                          → list[FeedbackItem]
    apply_feedback(session, feedback, api_key)    → dict[int, ChapterContent]
"""
from __future__ import annotations

import re
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FeedbackItem:
    """One discrete piece of supervisor feedback."""
    chapter:     int         # 1–5, 0 = unknown/general
    comment:     str         # the original comment text
    instruction: str         # converted to revision instruction
    priority:    str = "normal"  # high | normal | low

    def __repr__(self):
        return f"[Ch{self.chapter}] {self.comment[:60]}"


# Chapter keyword mapping
_CH_KEYWORDS = {
    1: ["introduction", "background", "problem statement", "objectives",
        "significance", "scope", "chapter one", "chapter 1",
        "in chapter one", "statement of the problem", "definition of terms"],
    2: ["literature", "review", "theoretical framework", "conceptual",
        "empirical", "chapter two", "chapter 2"],
    3: ["methodology", "research design", "sample", "sampling", "instrument",
        "validity", "reliability", "method", "chapter three", "chapter 3"],
    4: ["data", "analysis", "findings", "results", "hypothesis", "table",
        "chapter four", "chapter 4", "discussion"],
    5: ["conclusion", "recommendation", "summary", "chapter five", "chapter 5", "restates the findings", "implications"],
}


def parse_feedback(text: str) -> list[FeedbackItem]:
    """
    Parse supervisor feedback text into structured FeedbackItems.

    Handles:
    - Numbered lists (1. ... / i. ... / • ...)
    - Chapter references ("In Chapter 2...", "The literature review...")
    - Free-form paragraphs (treated as general feedback → Ch 1 default)
    """
    items: list[FeedbackItem] = []
    segments = _split_into_segments(text)

    for seg in segments:
        seg = seg.strip()
        if not seg or len(seg) < 15:
            continue
        ch  = _detect_chapter(seg)
        instr = _to_instruction(seg)
        priority = "high" if any(w in seg.lower() for w in
                                 ["must", "critical", "major", "fail", "rewrite", "completely"]) \
                   else "normal"
        items.append(FeedbackItem(chapter=ch, comment=seg,
                                  instruction=instr, priority=priority))

    # Deduplicate by similarity
    seen: list[str] = []
    unique = []
    for item in items:
        key = item.comment[:40].lower()
        if key not in seen:
            seen.append(key)
            unique.append(item)

    return unique


def _split_into_segments(text: str) -> list[str]:
    """Split feedback text into individual comments."""
    # Try numbered/bulleted list first
    items = re.findall(
        r'(?:^|\n)\s*(?:\d+[\.\)]|[ivxIVX]+[\.\)]|[\-•\*])\s*(.+?)(?=\n\s*(?:\d+[\.\)]|[ivxIVX]+[\.\)]|[\-•\*])|\Z)',
        text, re.DOTALL
    )
    if items and len(items) >= 2:
        return [i.strip() for i in items]
    # Fall back: split by sentence/paragraph
    paras = [p.strip() for p in re.split(r'\n\n+|\n(?=[A-Z])', text) if p.strip()]
    if paras:
        return paras
    return [text]


def _detect_chapter(text: str) -> int:
    """Detect which chapter this comment refers to."""
    text_l = text.lower()
    # Explicit "chapter N" reference — handle both digits and words
    m = re.search(r'chapter\s+(one|two|three|four|five|[1-5])', text_l)
    if m:
        val = m.group(1).strip()
        mapping = {"one":1,"two":2,"three":3,"four":4,"five":5}
        try:
            return int(val)
        except ValueError:
            return mapping.get(val, 1)
    # Keyword matching — score each chapter
    scores = {ch: 0 for ch in range(1, 6)}
    for ch, keywords in _CH_KEYWORDS.items():
        for kw in keywords:
            if kw in text_l:
                scores[ch] += 1
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else 1  # default to Ch 1


def _to_instruction(comment: str) -> str:
    """Convert a supervisor comment into a revision instruction."""
    comment = comment.strip().rstrip(".")
    # Already starts with an imperative — use as-is
    if re.match(r'^(add|expand|remove|clarify|improve|strengthen|rewrite|revise|include|ensure|make|fix|correct|develop)', 
                comment.lower()):
        return comment
    # Wrap negative feedback
    if any(w in comment.lower() for w in ["too", "not enough", "insufficient", "lacks", "missing", "unclear", "vague", "weak"]):
        return f"Address the following supervisor feedback: {comment}"
    # General instruction
    return f"Revise this section based on supervisor feedback: {comment}"


def apply_feedback(
    session,
    feedback:  list[FeedbackItem],
    api_key:   str | None = None,
    model:     str        = "gpt-4o",
) -> dict[int, "ChapterContent"]:
    """
    Apply a list of FeedbackItems to the relevant chapters.

    Groups multiple comments for the same chapter into a single
    combined revision to minimise API calls.

    Returns
    -------
    dict[chapter_number, ChapterContent] — revised chapters
    """
    from research_engine.writer.chapter_writer import revise_chapter

    # Group by chapter
    by_chapter: dict[int, list[str]] = {}
    for item in feedback:
        ch = item.chapter if item.chapter in range(1, 6) else 1
        by_chapter.setdefault(ch, []).append(item.instruction)

    revised = {}
    for ch_num, instructions in sorted(by_chapter.items()):
        if session.get_chapter(ch_num) is None:
            continue  # skip chapters not yet written
        combined = (
            f"Apply ALL of the following supervisor feedback items to this chapter:\n\n"
            + "\n".join(f"{i+1}. {instr}" for i, instr in enumerate(instructions))
        )
        try:
            result = revise_chapter(session, ch_num, combined,
                                    api_key=api_key, model=model)
            revised[ch_num] = result
        except Exception as exc:
            pass  # partial failure — continue with other chapters

    return revised

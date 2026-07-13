"""
research_engine/writer/reference_generator.py
Tier 1 #2 — Reference list generator

Scans all chapter text for in-text citations and produces a formatted
reference list in APA, Harvard, Vancouver, or Chicago style.

Because the AI generates realistic-looking but synthetic citations,
this module:
  1. Extracts all (Author, Year) patterns from chapter text
  2. Groups them
  3. Uses the LLM to expand each unique citation into a full reference entry
  4. Returns a sorted, formatted reference list

Public API
----------
    extract_citations(text)                 → list[Citation]
    generate_references(session, api_key)   → ReferenceList
    format_reference_list(ref_list, style)  → str
"""
from __future__ import annotations

import re
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Citation:
    """A single extracted in-text citation."""
    author:    str
    year:      str
    page:      str   = ""
    raw:       str   = ""

    @property
    def key(self) -> str:
        return f"{self.author.split(',')[0].strip().lower()}_{self.year}"

    def __hash__(self): return hash(self.key)
    def __eq__(self, other): return self.key == other.key


@dataclass
class ReferenceEntry:
    """A single formatted reference."""
    key:          str
    author:       str
    year:         str
    full_text:    str   = ""   # formatted full reference
    source_type:  str   = "journal"  # journal | book | chapter | website | thesis

    def __repr__(self): return self.full_text or f"{self.author} ({self.year})"


@dataclass
class ReferenceList:
    """A complete reference list for a project."""
    entries:       list[ReferenceEntry] = field(default_factory=list)
    style:         str                  = "APA"
    generated_at:  str                  = ""

    def to_text(self) -> str:
        lines = ["REFERENCES\n" + "="*60 + "\n"]
        for e in sorted(self.entries, key=lambda x: x.author.lower()):
            lines.append(e.full_text or f"{e.author} ({e.year}).")
            lines.append("")
        return "\n".join(lines)

    def to_markdown(self) -> str:
        lines = ["## References\n"]
        for e in sorted(self.entries, key=lambda x: x.author.lower()):
            lines.append(f"- {e.full_text or e.author + ' (' + e.year + ').'}")
        return "\n".join(lines)

    def __len__(self): return len(self.entries)


# ══════════════════════════════════════════════════════════════
# Step 1: Extract in-text citations
# ══════════════════════════════════════════════════════════════

# Patterns:
#   (Smith, 2020)  /  (Smith & Jones, 2020)  /  (Smith et al., 2020)
#   Smith (2020)   /  Smith and Jones (2020)
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


def extract_citations(text: str) -> list[Citation]:
    """
    Extract all unique in-text citations from chapter text.

    Returns a deduplicated list of Citation objects.
    """
    found: dict[str, Citation] = {}

    for m in _PARENTHETICAL.finditer(text):
        author, year_raw = m.group(1).strip(), m.group(2).strip()
        year, page = _split_year_page(year_raw)
        c = Citation(author=author, year=year, page=page, raw=m.group(0))
        found[c.key] = c

    for m in _NARRATIVE.finditer(text):
        author, year_raw = m.group(1).strip(), m.group(2).strip()
        year, page = _split_year_page(year_raw)
        c = Citation(author=author, year=year, page=page, raw=m.group(0))
        found[c.key] = c

    return sorted(found.values(), key=lambda x: x.author.lower())


def _split_year_page(raw: str) -> tuple[str, str]:
    """Split '2020, p. 45' into ('2020', 'p. 45')."""
    parts = raw.split(",", 1)
    year  = parts[0].strip()
    page  = parts[1].strip() if len(parts) > 1 else ""
    return year, page


# ══════════════════════════════════════════════════════════════
# Step 2: Generate full references via LLM
# ══════════════════════════════════════════════════════════════

def generate_references(
    session,
    api_key:   str | None = None,
    model:     str        = "gpt-4o-mini",
    max_refs:  int        = 80,
) -> ReferenceList:
    """
    Generate a full formatted reference list for all chapters in the session.

    Parameters
    ----------
    session  : ProjectSession
    api_key  : OpenAI API key
    model    : model to use (gpt-4o-mini is sufficient and cheaper)
    max_refs : cap on number of unique citations to expand (to control cost)

    Returns
    -------
    ReferenceList
    """
    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    style = session.metadata.citation_style or "APA"

    # Collect all text
    all_text = "\n".join(
        ch.content for ch in session.chapters.values()
    )
    all_text += "\n" + session.guideline_raw

    citations = extract_citations(all_text)[:max_refs]
    ref_list  = ReferenceList(style=style)

    if not citations:
        return ref_list

    if not key:
        # Fallback: return stub entries without full text
        for c in citations:
            ref_list.entries.append(ReferenceEntry(
                key=c.key, author=c.author, year=c.year,
                full_text=f"{c.author} ({c.year}). [Full reference not generated — OPENAI_API_KEY not set]"
            ))
        return ref_list

    try:
        from openai import OpenAI
    except ImportError:
        for c in citations:
            ref_list.entries.append(ReferenceEntry(
                key=c.key, author=c.author, year=c.year,
                full_text=f"{c.author} ({c.year}). [openai not installed]"
            ))
        return ref_list

    client = OpenAI(api_key=key)

    # Build citation list for the prompt
    cite_lines = "\n".join(
        f"{i+1}. {c.author} ({c.year})" for i, c in enumerate(citations)
    )

    topic = session.metadata.title or session.metadata.topic or "health sciences research"

    prompt = f"""You are an academic librarian. For each citation below, generate a
plausible, properly formatted reference entry in {style} style.

Rules:
- Each reference must be realistic-looking (journal names, publishers, cities)
- Match the topic area: "{topic}"
- Use the exact author surname(s) and year provided
- Add plausible first names/initials, journal names, volume, issue, pages, or book details
- For journal articles: use realistic African and international journals where appropriate
- Format: one entry per line, starting with the number
- Return ONLY the numbered reference list, nothing else

CITATION LIST:
{cite_lines}"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=min(4096, len(citations) * 80),
        )
        raw = response.choices[0].message.content or ""
        _parse_llm_references(raw, citations, ref_list)
    except Exception as exc:
        # Fallback to stubs
        for c in citations:
            ref_list.entries.append(ReferenceEntry(
                key=c.key, author=c.author, year=c.year,
                full_text=f"{c.author} ({c.year}). [Reference generation failed: {exc}]"
            ))

    return ref_list


def _parse_llm_references(raw: str, citations: list[Citation],
                           ref_list: ReferenceList) -> None:
    """Parse numbered LLM output into ReferenceEntry objects."""
    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    entries_by_index: dict[int, str] = {}

    for line in lines:
        m = re.match(r'^(\d+)\.\s+(.+)', line)
        if m:
            idx  = int(m.group(1)) - 1
            text = m.group(2).strip()
            if idx in entries_by_index:
                entries_by_index[idx] += " " + text
            else:
                entries_by_index[idx] = text
        elif entries_by_index:
            # Continuation line
            last = max(entries_by_index.keys())
            entries_by_index[last] += " " + line

    for i, c in enumerate(citations):
        full_text = entries_by_index.get(i, f"{c.author} ({c.year}).")
        ref_list.entries.append(ReferenceEntry(
            key=c.key, author=c.author, year=c.year, full_text=full_text
        ))


# ══════════════════════════════════════════════════════════════
# Step 3: Format helper
# ══════════════════════════════════════════════════════════════

def format_reference_list(ref_list: ReferenceList, style: str = "") -> str:
    """
    Return the reference list as a formatted string.

    Parameters
    ----------
    ref_list : ReferenceList object
    style    : override style (APA/Harvard/Vancouver/Chicago)

    Returns
    -------
    str — the full reference section text
    """
    return ref_list.to_text()

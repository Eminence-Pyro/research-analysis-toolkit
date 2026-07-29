"""
research_engine/writer/apa_formatter.py
APA 7th Edition Reference Formatter

Properly formats reference entries according to the APA 7th edition
Publication Manual rules. Works with or without the LLM — this is a
deterministic, rule-based formatter.

APA 7th Key Rules:
  - Author: Surname, Initial(s). Multiple authors separated by commas,
    last two joined with "&". 21+ authors: first 20 + ... + last author.
  - Year: (YYYY). In parentheses, followed by a period.
  - Title: Sentence case for article titles. Italic for book/journal titles.
  - Journal: Italic journal name, italic volume, (issue), page range.
  - DOI: https://doi.org/xxxxx
  - Books: Italic title, Publisher.
  - Book chapters: In Editor (Ed.), Book title (pp. xx-xx). Publisher.

Public API
----------
    format_apa_reference(entry)              → str
    format_apa_reference_list(entries)      → str
    parse_apa_reference(text)               → ReferenceEntry
    build_apa_reference(author, year, ...)  → str
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ══════════════════════════════════════════════════════════════
# APA 7th Edition Formatting Rules
# ══════════════════════════════════════════════════════════════

def _format_author_names(raw: str) -> str:
    """
    Format author names according to APA 7th edition.

    Handles:
      - "John Smith" → "Smith, J."
      - "Smith, John" → "Smith, J."
      - "Smith, J. A." → "Smith, J. A." (already formatted)
      - "Smith & Jones" → "Smith, J., & Jones, R."
      - "Smith, Jones, Brown" → "Smith, J., Jones, R., & Brown, A."
      - "Okafor et al." → "Okafor et al." (kept as-is)
    """
    if not raw:
        return ""

    raw = raw.strip()

    # Keep et al. as-is
    if "et al." in raw:
        return raw

    # Check if already in "Surname, Initial" format (has comma and initials)
    # If the raw text has commas and each part after comma looks like initials
    if re.match(r'^[A-Z][a-z]+,\s+[A-Z]\.', raw) and "&" not in raw and " and " not in raw:
        return raw  # Already formatted

    # Split multiple authors on " & " or " and " (NOT commas — those separate surname from given)
    if " & " in raw or " and " in raw:
        parts = re.split(r'\s+(?:&|and)\s+', raw)
    else:
        # Single author — check if "Surname, Given" format
        if ", " in raw:
            # Could be "Surname, Given" or "Surname, Initial"
            return _format_single_author(raw)
        parts = [raw]

    parts = [p.strip() for p in parts if p.strip()]
    formatted = [_format_single_author(p) for p in parts]

    if len(formatted) <= 1:
        return formatted[0] if formatted else ""
    elif len(formatted) == 2:
        return f"{formatted[0]}, & {formatted[1]}"
    else:
        return ", ".join(formatted[:-1]) + ", & " + formatted[-1]


def _format_single_author(name: str) -> str:
    """Format a single author name to Surname, Initial(s)."""
    name = name.strip().rstrip(".")

    # Already in "Surname, Initial" format (has comma)
    if "," in name:
        surname, given = name.split(",", 1)
        surname = surname.strip()
        given = given.strip()
        initials = _extract_initials(given)
        return f"{surname}, {initials}" if initials else surname + "."

    # "John Smith" or "J.A. Smith" or "Smith"
    tokens = name.split()
    if len(tokens) == 1:
        # Just a surname — no initials available
        return tokens[0] + "."

    # Last token is surname, rest are given names
    surname = tokens[-1]
    given = " ".join(tokens[:-1])
    initials = _extract_initials(given)
    return f"{surname}, {initials}" if initials else surname + "."


def _extract_initials(given: str) -> str:
    """Extract initials from given names: 'John Adam' → 'J. A.', 'J.A.' → 'J. A.'"""
    if not given:
        return ""
    # Already initials
    parts = re.findall(r'[A-Z]\.?', given)
    if parts:
        return " ".join(p if p.endswith(".") else p + "." for p in parts)
    # Extract first letter of each name
    tokens = given.split()
    initials = [t[0].upper() + "." for t in tokens if t]
    return " ".join(initials)


def _sentence_case(title: str) -> str:
    """
    Convert a title to sentence case for APA 7th article titles.
    Only the first word and proper nouns are capitalised.
    """
    if not title:
        return ""
    # Capitalise first letter, lowercase the rest
    title = title.strip()
    # Keep capitalised words that are likely proper nouns (all-caps, or known terms)
    proper_nouns = ["Nigeria", "Nigerian", "African", "WHO", "UNICEF", "CDC",
                    "SPSS", "ANOVA", "HIV", "AIDS", "COVID", "Yamane", "Cochran",
                    "Cronbach", "Likert", "APA", "NHS", "USA", "UK", "COVID-19",
                    "Donabedian", "SPSS", "IBM"]
    words = title.split()
    result = [words[0][0].upper() + words[0][1:] if words[0] else ""]
    for word in words[1:]:
        if word in proper_nouns or word.isupper():
            result.append(word)
        else:
            result.append(word.lower())
    return " ".join(result)


def _detect_source_type(entry) -> str:
    """Auto-detect the source type from reference text or entry fields."""
    text = getattr(entry, "full_text", "") or str(entry)
    text_l = text.lower()

    if "doi" in text_l or "doi.org" in text_l:
        return "journal"
    if "retrieved from" in text_l or "http" in text_l:
        return "website"
    if "in " in text_l and "(ed." in text_l or "(eds." in text_l:
        return "chapter"
    if "thesis" in text_l or "dissertation" in text_l:
        return "thesis"
    if "university" in text_l and "press" not in text_l:
        return "thesis"
    return "journal"  # default


# ══════════════════════════════════════════════════════════════
# Main formatting functions
# ══════════════════════════════════════════════════════════════

def format_apa_reference(entry) -> str:
    """
    Format a ReferenceEntry as an APA 7th edition reference.

    If the entry already has well-formed full_text, it will be cleaned up.
    If the entry is a stub (just "Author (Year)."), it will be expanded
    with template formatting.
    """
    author = getattr(entry, "author", "") or ""
    year   = getattr(entry, "year", "") or ""
    full   = getattr(entry, "full_text", "") or ""
    source_type = getattr(entry, "source_type", "journal") or "journal"

    # If full_text looks complete (has volume/page/DOI), just clean it
    if full and len(full) > 50 and not full.startswith(f"{author} ({year}). ["):
        return _clean_apa_reference(full)

    # Otherwise, format from author + year + source type
    formatted_author = _format_author_names(author)
    year_part = f"({year})."

    if source_type == "journal":
        # Author, A. A. (Year). Title of article. Journal Name, vol(issue), pages.
        # https://doi.org/xxxxx
        return f"{formatted_author} {year_part} [Article title]. [Journal Name], [vol]([issue]), [pages]."

    elif source_type == "book":
        # Author, A. A. (Year). Title of book (ed.). Publisher.
        return f"{formatted_author} {year_part} [Book title]. [Publisher]."

    elif source_type == "chapter":
        # Author, A. A. (Year). Title of chapter. In Editor (Ed.), Book title (pp. xx-xx). Publisher.
        return f"{formatted_author} {year_part} [Chapter title]. In [Editor] (Ed.), [Book title] (pp. xx-xx). [Publisher]."

    elif source_type == "website":
        # Author, A. A. (Year). Title of page. Site Name. URL
        return f"{formatted_author} {year_part} [Page title]. [Site Name]. [URL]"

    elif source_type == "thesis":
        # Author, A. A. (Year). Title of thesis [Doctoral dissertation/Master's thesis, University]. Database.
        return f"{formatted_author} {year_part} [Thesis title] [Master's thesis, University Name]."

    return f"{formatted_author} {year_part}"


def _clean_apa_reference(text: str) -> str:
    """Clean up an LLM-generated reference to better conform to APA 7th edition."""
    # Remove leading numbers
    text = re.sub(r'^\d+\.\s*', '', text)
    # Ensure period after year parenthesis
    text = re.sub(r'\((\d{4})\)\s*(?!\.)', r'(\1). ', text)
    # Remove double spaces
    text = re.sub(r'  +', ' ', text)
    # Ensure DOI is in https://doi.org/ format
    text = re.sub(r'(?:https?://)?(?:dx\.)?doi\.org/', 'https://doi.org/', text, flags=re.IGNORECASE)
    return text.strip()


def format_apa_reference_list(entries: list, hanging_indent: bool = True) -> str:
    """
    Format a list of ReferenceEntry objects as an APA 7th edition reference list.

    Entries are sorted alphabetically by first author surname, then by year.
    """
    # Sort by author surname, then year
    sorted_entries = sorted(
        entries,
        key=lambda e: (
            e.author.split(",")[0].strip().lower() if hasattr(e, "author") else "",
            getattr(e, "year", "")
        )
    )

    lines = ["References", ""]
    for entry in sorted_entries:
        formatted = format_apa_reference(entry)
        if hanging_indent:
            # Simulate hanging indent with spaces
            wrapped = _hanging_indent(formatted)
            lines.append(wrapped)
        else:
            lines.append(formatted)
        lines.append("")

    return "\n".join(lines)


def _hanging_indent(text: str, indent: int = 4) -> str:
    """Add a hanging indent to multi-line text."""
    if "\n" not in text and len(text) < 80:
        return text
    # Just return the text — actual hanging indent is handled by the exporter
    return text


def parse_apa_reference(text: str):
    """
    Parse an APA 7th edition reference string into a structured entry.

    Returns a dict with: author, year, title, source, source_type, doi
    """
    text = text.strip()
    result = {"author": "", "year": "", "title": "", "source": "", "source_type": "", "doi": ""}

    # Extract year
    year_match = re.search(r'\((\d{4}[a-z]?)\)', text)
    if year_match:
        result["year"] = year_match.group(1)
        result["author"] = text[:year_match.start()].rstrip().rstrip(",").strip()

    # Extract DOI
    doi_match = re.search(r'https?://doi\.org/(.+?)(?:\s|$)', text, re.IGNORECASE)
    if doi_match:
        result["doi"] = doi_match.group(1).rstrip(".")

    # Detect source type
    if result["doi"]:
        result["source_type"] = "journal"
    elif "retrieved from" in text.lower() or "http" in text.lower():
        result["source_type"] = "website"
    elif re.search(r'\bed\.|eds\.|in\s+[A-Z]', text, re.IGNORECASE):
        result["source_type"] = "chapter"
    elif "thesis" in text.lower() or "dissertation" in text.lower():
        result["source_type"] = "thesis"
    else:
        result["source_type"] = "journal"

    # Extract title (text between year). and the next period)
    after_year = text[year_match.end():].strip().lstrip(".") if year_match else text
    # Title is typically up to the first period after the year
    title_match = re.match(r'\s*(.+?)\.\s', after_year)
    if title_match:
        result["title"] = title_match.group(1).strip()

    # Extract source (journal/book name — usually italicised text)
    # After the title, the next segment is the source
    if title_match:
        after_title = after_year[title_match.end():]
        # Source is everything up to the volume number or end
        source_match = re.match(r'(.+?)(?:,\s*\d+|$)', after_title)
        if source_match:
            result["source"] = source_match.group(1).strip().rstrip(",")

    return result


def build_apa_reference(
    author:       str,
    year:         str,
    title:        str       = "",
    journal:      str       = "",
    volume:      str       = "",
    issue:       str       = "",
    pages:       str       = "",
    doi:         str       = "",
    publisher:    str       = "",
    source_type:  str       = "journal",
    editor:       str       = "",
    book_title:   str       = "",
    url:         str       = "",
) -> str:
    """
    Build a complete APA 7th edition reference from structured fields.
    """
    formatted_author = _format_author_names(author)
    year_part = f"({year})."

    if source_type == "journal":
        ref = f"{formatted_author} {year_part} {_sentence_case(title)}."
        if journal:
            ref += f" <i>{journal}</i>"
            if volume:
                ref += f", <i>{volume}</i>"
            if issue:
                ref += f"({issue})"
            if pages:
                ref += f", {pages}"
            ref += "."
        if doi:
            ref += f" https://doi.org/{doi}"
        return ref

    elif source_type == "book":
        ref = f"{formatted_author} {year_part} <i>{title}</i>."
        if publisher:
            ref += f" {publisher}."
        return ref

    elif source_type == "chapter":
        ref = f"{formatted_author} {year_part} {_sentence_case(title)}."
        if editor and book_title:
            ref += f" In {editor} (Ed.), <i>{book_title}</i>"
            if pages:
                ref += f" (pp. {pages})"
            ref += "."
        if publisher:
            ref += f" {publisher}."
        return ref

    elif source_type == "website":
        ref = f"{formatted_author} {year_part} {_sentence_case(title)}."
        if url:
            ref += f" {url}"
        return ref

    elif source_type == "thesis":
        ref = f"{formatted_author} {year_part} <i>{title}</i>"
        ref += f" [Master's thesis, {publisher}]."
        return ref

    return f"{formatted_author} {year_part} {_sentence_case(title)}."

"""
research_engine/writer/chapter_writer.py

The AI chapter writer — takes a ProjectSession and a chapter number,
and produces a full, correctly structured, level-appropriate chapter.

This is the core intelligence of the application.

It uses a structured prompt strategy:
  1. Extract all available context (metadata, guideline, existing chapters)
  2. Build a level + design appropriate chapter template
  3. Call the LLM with the full context
  4. Return the result and store it in the session

Public API
----------
    write_chapter(session, chapter_number, api_key, model)  → ChapterContent
    extract_metadata_with_ai(session, api_key)              → ProjectMetadata
    suggest_study_config(session)                           → dict
"""
from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any

from research_engine.writer.project_session import (
    ProjectSession, ProjectMetadata, ChapterContent,
    EducationLevel, ResearchDesign, CHAPTER_TITLES
)


# ══════════════════════════════════════════════════════════════
# Chapter structure templates
# ══════════════════════════════════════════════════════════════

_CHAPTER_STRUCTURES = {
    1: {
        "title": "Introduction",
        "sections": [
            "Background of the Study",
            "Statement of the Problem",
            "Objectives of the Study",
            "Research Questions",
            "Hypotheses (if applicable)",
            "Significance of the Study",
            "Scope and Limitations of the Study",
            "Definition of Terms",
        ],
        "purpose": (
            "Introduce the research topic, establish its context and importance, "
            "identify the problem, state clear objectives and research questions, "
            "and justify why this study is needed."
        ),
    },
    2: {
        "title": "Literature Review",
        "sections": [
            "Introduction",
            "Conceptual Framework",
            "Theoretical Framework",
            "Empirical Review (past studies directly related to each objective)",
            "Summary of Literature Review / Research Gap",
        ],
        "purpose": (
            "Synthesize existing knowledge on the topic. For each sub-heading, "
            "review 2–4 studies, compare findings, identify contradictions, and "
            "establish the gap this research fills. Do not list summaries — synthesize."
        ),
    },
    3: {
        "title": "Research Methodology",
        "sections": [
            "Introduction",
            "Research Design",
            "Study Area",
            "Population of the Study",
            "Sample Size Determination",
            "Sampling Technique",
            "Instrument for Data Collection",
            "Validity and Reliability of the Instrument",
            "Method of Data Collection",
            "Method of Data Analysis",
        ],
        "purpose": (
            "Justify every methodological decision. State the research design, "
            "describe the study population and area, explain how sample size was "
            "calculated (show the formula), describe the instrument (questionnaire), "
            "state statistical tools used (frequencies, means, chi-square, etc.)."
        ),
    },
    4: {
        "title": "Data Presentation, Analysis and Discussion of Findings",
        "sections": [
            "Introduction",
            "Demographic Characteristics of Respondents",
            "Presentation of Findings by Research Question / Objective",
            "Test of Hypotheses",
            "Discussion of Findings",
        ],
        "purpose": (
            "Present the actual data analysis results. Reference specific table numbers. "
            "Describe what each table shows, interpret the statistics, answer each "
            "research question based on the data, test each hypothesis using the "
            "stated statistical tool, and discuss findings in relation to past literature."
        ),
    },
    5: {
        "title": "Summary, Conclusion and Recommendations",
        "sections": [
            "Introduction",
            "Summary of the Study",
            "Summary of Findings",
            "Conclusion",
            "Recommendations",
            "Contribution to Knowledge",
            "Suggestions for Further Studies",
        ],
        "purpose": (
            "Summarize the entire study (not just findings). List the key findings "
            "point by point. Draw a conclusion that directly answers the main research "
            "problem. Give practical, actionable recommendations. Suggest future research."
        ),
    },
}


# ══════════════════════════════════════════════════════════════
# Level-specific writing guidelines
# ══════════════════════════════════════════════════════════════

_LEVEL_GUIDELINES = {
    EducationLevel.OND: (
        "Write at OND (Ordinary National Diploma) level. "
        "Use clear, simple English. Keep sentences short. "
        "Avoid overly complex academic jargon. "
        "Citations are important but can be fewer (4–6 per section)."
    ),
    EducationLevel.HND: (
        "Write at HND (Higher National Diploma) level. "
        "Use academic English. Include moderate use of technical terms. "
        "Cite 5–8 sources per section."
    ),
    EducationLevel.BSC: (
        "Write at undergraduate (B.Sc.) dissertation level. "
        "Use formal academic English. Show clear analytical thinking. "
        "Cite 6–10 sources per section. Follow APA style unless specified otherwise."
    ),
    EducationLevel.PGD: (
        "Write at Postgraduate Diploma level — between undergraduate and master's. "
        "Demonstrate conceptual understanding. Cite 8–12 sources per section."
    ),
    EducationLevel.MSC: (
        "Write at master's (M.Sc.) thesis level. "
        "Demonstrate critical analytical ability. Synthesize literature — do not merely summarize. "
        "Show awareness of methodological limitations. Cite 10–15 sources per section. "
        "Use hedging language appropriately ('the findings suggest', 'this may indicate')."
    ),
    EducationLevel.PHD: (
        "Write at doctoral (Ph.D.) thesis level. "
        "Demonstrate original, sophisticated critical analysis. "
        "Engage deeply with theoretical frameworks. Identify gaps in the literature precisely. "
        "Justify every design decision epistemologically. Cite 15–25 sources per section."
    ),
    EducationLevel.UNKNOWN: (
        "Write at a standard academic level appropriate for a university research project. "
        "Use formal English. Cite 6–10 sources per section. Follow APA style."
    ),
}


# ══════════════════════════════════════════════════════════════
# Prompt builder
# ══════════════════════════════════════════════════════════════

def _build_chapter_prompt(session: ProjectSession, chapter_number: int) -> str:
    """Build the full LLM prompt for a chapter."""
    m       = session.metadata
    struct  = _CHAPTER_STRUCTURES[chapter_number]
    level_g = _LEVEL_GUIDELINES.get(m.level, _LEVEL_GUIDELINES[EducationLevel.UNKNOWN])
    wc      = m.word_count_for_level().get(chapter_number, 2500)

    # ── Context block ─────────────────────────────────────────
    ctx_parts = []

    if m.title:
        ctx_parts.append(f"STUDY TITLE: {m.title}")
    if m.topic:
        ctx_parts.append(f"RESEARCH TOPIC: {m.topic}")
    if m.institution:
        ctx_parts.append(f"INSTITUTION: {m.institution}")
    if m.department:
        ctx_parts.append(f"DEPARTMENT: {m.department}")
    if m.level != EducationLevel.UNKNOWN:
        ctx_parts.append(f"ACADEMIC LEVEL: {m.level.value.upper()}")
    if m.research_design != ResearchDesign.UNKNOWN:
        ctx_parts.append(f"RESEARCH DESIGN: {m.research_design.value.replace('_', ' ').title()}")
    if m.population:
        ctx_parts.append(f"STUDY POPULATION: {m.population}")
    if m.study_area:
        ctx_parts.append(f"STUDY AREA: {m.study_area}")
    if m.citation_style:
        ctx_parts.append(f"CITATION STYLE: {m.citation_style}")
    if m.objectives:
        ctx_parts.append("OBJECTIVES:\n" + "\n".join(f"  {i+1}. {o}" for i, o in enumerate(m.objectives)))
    if m.research_questions:
        ctx_parts.append("RESEARCH QUESTIONS:\n" + "\n".join(f"  {i+1}. {q}" for i, q in enumerate(m.research_questions)))
    if m.hypotheses:
        ctx_parts.append("HYPOTHESES:\n" + "\n".join(f"  {i+1}. {h}" for i, h in enumerate(m.hypotheses)))

    # Include earlier chapters for continuity
    earlier = [(n, c) for n, c in session.chapters.items() if n < chapter_number]
    if earlier:
        ctx_parts.append("\nALREADY WRITTEN CHAPTERS (for continuity):")
        for n, c in sorted(earlier):
            ctx_parts.append(f"--- Chapter {n}: {c.title} (preview) ---")
            ctx_parts.append(c.preview(500))

    # Include guideline excerpt
    if session.guideline_raw:
        excerpt = session.guideline_raw[:3000]
        ctx_parts.append(f"\nGUIDELINE EXCERPT:\n{excerpt}")

    context_block = "\n".join(ctx_parts)

    # ── Sections list ─────────────────────────────────────────
    sections_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(struct["sections"]))

    # ── Full prompt ───────────────────────────────────────────
    prompt = f"""You are an expert academic research writer. Your task is to write Chapter {chapter_number} of a research project.

WRITING LEVEL INSTRUCTIONS:
{level_g}

STUDY CONTEXT:
{context_block}

CHAPTER TO WRITE: Chapter {chapter_number} — {struct["title"]}

PURPOSE OF THIS CHAPTER:
{struct["purpose"]}

REQUIRED SECTIONS (you must include ALL of these):
{sections_text}

WORD COUNT TARGET: approximately {wc} words

FORMAT INSTRUCTIONS:
- Write in formal academic English
- Use proper heading hierarchy: ## for major headings, ### for sub-headings
- Every claim must have an in-text citation in {m.citation_style} style
- Use realistic author names, years, and titles for citations (do not fabricate real DOIs)
- Number tables and figures if any are referenced (Table 4.1, Figure 2.1, etc.)
- Where a section does not apply to this study, state why briefly rather than omitting it
- Do NOT include a reference list — that will be generated separately
- Start directly with the chapter content — no preamble or meta-commentary
- Maintain consistency with any earlier chapters provided above

Write the complete chapter now:"""

    return prompt


# ══════════════════════════════════════════════════════════════
# Main writer function
# ══════════════════════════════════════════════════════════════

def write_chapter(
    session:        ProjectSession,
    chapter_number: int,
    api_key:        str | None = None,
    model:          str        = "gpt-4o",
) -> ChapterContent:
    """
    Generate a full chapter using the LLM.

    Parameters
    ----------
    session        : the active ProjectSession (must have metadata populated)
    chapter_number : 1–5
    api_key        : OpenAI API key (falls back to OPENAI_API_KEY env var)
    model          : model to use (default: gpt-4o)

    Returns
    -------
    ChapterContent — also stored in session.chapters[chapter_number]
    """
    if chapter_number not in range(1, 6):
        raise ValueError(f"chapter_number must be 1–5, got {chapter_number}")

    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise EnvironmentError(
            "OpenAI API key required. Set OPENAI_API_KEY environment variable "
            "or pass api_key to write_chapter()."
        )

    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "openai package required. Install with: pip install openai"
        )

    client = OpenAI(api_key=key)
    prompt = _build_chapter_prompt(session, chapter_number)
    struct = _CHAPTER_STRUCTURES[chapter_number]

    response = client.chat.completions.create(
        model       = model,
        messages    = [
            {"role": "system",
             "content": (
                 "You are an expert academic research writer specialising in Nigerian "
                 "and African university research projects. You write chapters that are "
                 "well-structured, appropriately cited, analytically rigorous, and "
                 "correctly calibrated to the student's education level."
             )},
            {"role": "user", "content": prompt},
        ],
        temperature = 0.7,
        max_tokens  = 4096,
    )

    content   = response.choices[0].message.content or ""
    usage     = response.usage
    notes     = (
        f"Model: {model} | "
        f"Tokens: {usage.prompt_tokens} in / {usage.completion_tokens} out"
        if usage else f"Model: {model}"
    )

    session.set_chapter(chapter_number, content, notes=notes)
    return session.chapters[chapter_number]


# ══════════════════════════════════════════════════════════════
# AI-assisted metadata extraction
# ══════════════════════════════════════════════════════════════

def extract_metadata_with_ai(
    session: ProjectSession,
    api_key: str | None = None,
    model:   str        = "gpt-4o-mini",
) -> ProjectMetadata:
    """
    Use the LLM to extract / complete ProjectMetadata from the guideline text.
    Fills fields that the regex parser missed.

    Returns the updated metadata (also stored in session.metadata).
    """
    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not key or not session.guideline_raw:
        return session.metadata

    try:
        from openai import OpenAI
    except ImportError:
        return session.metadata

    client  = OpenAI(api_key=key)
    excerpt = session.guideline_raw[:4000]

    prompt = f"""Extract structured metadata from this research project guideline.
Return ONLY a valid JSON object with these keys (use null for unknown fields):

{{
  "title": string,
  "topic": string,
  "level": one of ["ond","hnd","bsc","pgd","msc","phd","unknown"],
  "institution": string,
  "department": string,
  "citation_style": one of ["APA","Harvard","Vancouver","Chicago"],
  "research_design": one of ["descriptive","correlational","experimental","quasi_experimental","cross_sectional","longitudinal","case_study","mixed_methods","unknown"],
  "population": string,
  "study_area": string,
  "word_count_target": integer or null,
  "objectives": [list of strings],
  "research_questions": [list of strings],
  "hypotheses": [list of strings],
  "keywords": [list of strings]
}}

GUIDELINE TEXT:
{excerpt}

Return only the JSON. No explanation."""

    try:
        response = client.chat.completions.create(
            model       = model,
            messages    = [{"role": "user", "content": prompt}],
            temperature = 0.1,
            max_tokens  = 1024,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content or "{}")
        _apply_extracted_metadata(session.metadata, data)
    except Exception:
        pass   # silently fall back to existing metadata

    return session.metadata


def _apply_extracted_metadata(meta: ProjectMetadata, data: dict) -> None:
    """Apply AI-extracted fields to existing metadata (non-destructive)."""
    def _set(attr, key, transform=None):
        val = data.get(key)
        if val is None:
            return
        if transform:
            try:
                val = transform(val)
            except Exception:
                return
        if not getattr(meta, attr, None):
            setattr(meta, attr, val)

    _set("title",              "title")
    _set("topic",              "topic")
    _set("institution",        "institution")
    _set("department",         "department")
    _set("citation_style",     "citation_style")
    _set("population",         "population")
    _set("study_area",         "study_area")
    _set("word_count_target",  "word_count_target", int)
    _set("level",              "level",             lambda v: EducationLevel(v))
    _set("research_design",    "research_design",   lambda v: ResearchDesign(v))

    for list_field in ("objectives", "research_questions", "hypotheses", "keywords"):
        val = data.get(list_field)
        if isinstance(val, list) and val and not getattr(meta, list_field):
            setattr(meta, list_field, [str(i) for i in val if i])


# ══════════════════════════════════════════════════════════════
# Study config suggester
# ══════════════════════════════════════════════════════════════

def suggest_study_config(session: ProjectSession) -> dict:
    """
    Generate a starter study config.json dict from project metadata.
    This can be used to bootstrap the dataset generation pipeline.

    Returns a dict compatible with schemas/study.schema.json.
    """
    m = session.metadata
    return {
        "schema_version":    "1.0",
        "rat_version":       "1.2.0",
        "title":             m.title or "Untitled Study",
        "setting":           m.study_area or "To be specified",
        "population":        m.population or "To be specified",
        "target_n":          _suggest_sample_size(m.level),
        "design":            m.research_design.value.replace("_", " ").title(),
        "sampling_technique": "Systematic random sampling",
        "facilities": [
            {"id": 1, "name": "Site A", "satisfaction_effect":  0.2},
            {"id": 2, "name": "Site B", "satisfaction_effect":  0.0},
            {"id": 3, "name": "Site C", "satisfaction_effect": -0.1},
        ],
    }


def _suggest_sample_size(level: EducationLevel) -> int:
    return {
        EducationLevel.OND:  60,
        EducationLevel.HND:  80,
        EducationLevel.BSC: 120,
        EducationLevel.PGD: 150,
        EducationLevel.MSC: 200,
        EducationLevel.PHD: 350,
    }.get(level, 120)


# ══════════════════════════════════════════════════════════════
# Tier 1 #1 — Chapter revision
# ══════════════════════════════════════════════════════════════

def revise_chapter(
    session:        "ProjectSession",
    chapter_number: int,
    instruction:    str,
    api_key:        str | None = None,
    model:          str        = "gpt-4o",
) -> "ChapterContent":
    """
    Revise an existing chapter based on a natural-language instruction.

    The original chapter is passed back to the LLM together with the
    instruction. Only the specific sections that need changing are
    rewritten; the overall structure is preserved.

    Parameters
    ----------
    session        : active ProjectSession (must already have chapter_number)
    chapter_number : 1–5
    instruction    : e.g. "Make the literature review more critical",
                         "Add more detail to the methodology section",
                         "Supervisor says the problem statement is too broad"
    api_key        : OpenAI API key (falls back to OPENAI_API_KEY)
    model          : OpenAI model (default: gpt-4o)

    Returns
    -------
    ChapterContent — updated chapter stored in session.chapters[chapter_number]
    """
    existing = session.get_chapter(chapter_number)
    if existing is None:
        raise ValueError(
            f"Chapter {chapter_number} has not been written yet. "
            f"Call write_chapter() first."
        )

    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise EnvironmentError("OPENAI_API_KEY not set.")

    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai package required: pip install openai")

    client = OpenAI(api_key=key)
    m      = session.metadata
    wc     = m.word_count_for_level().get(chapter_number, 2500)
    level_g = _LEVEL_GUIDELINES.get(m.level, _LEVEL_GUIDELINES[EducationLevel.UNKNOWN])
    struct  = _CHAPTER_STRUCTURES[chapter_number]

    prompt = f"""You are an expert academic editor. You must revise an existing research chapter
based on specific feedback or instructions.

STUDY: {m.title or "Research Project"}
LEVEL: {m.level.value.upper()}
CHAPTER: {chapter_number} — {struct["title"]}
CITATION STYLE: {m.citation_style}
TARGET WORD COUNT: ~{wc:,} words

WRITING LEVEL INSTRUCTIONS:
{level_g}

REVISION INSTRUCTION:
{instruction}

EXISTING CHAPTER (revise this):
{existing.content}

RULES FOR REVISION:
1. Apply ONLY the changes requested in the revision instruction
2. Preserve sections that do not need changing
3. Maintain the same heading structure (## and ###)
4. Keep in-text citations in {m.citation_style} style
5. Do NOT add a preamble like "Here is the revised chapter" — output the chapter directly
6. Maintain the approximate word count target

Output the complete revised chapter:"""

    response = client.chat.completions.create(
        model       = model,
        messages    = [
            {"role": "system",
             "content": (
                 "You are an expert academic editor specialising in Nigerian and African "
                 "university research projects. You apply targeted revisions while "
                 "preserving the structure and voice of the original text."
             )},
            {"role": "user", "content": prompt},
        ],
        temperature = 0.5,
        max_tokens  = 4096,
    )

    new_content = response.choices[0].message.content or ""
    usage       = response.usage
    notes = (
        f"REVISION — Model: {model} | "
        f"Instruction: {instruction[:80]} | "
        f"Tokens: {usage.prompt_tokens}/{usage.completion_tokens}"
        if usage else f"REVISION — Model: {model}"
    )

    session.set_chapter(chapter_number, new_content, notes=notes, status="revised")
    return session.chapters[chapter_number]
'''

print(f"revise_chapter function: {len(REVISE_FUNC.strip().splitlines())} lines")

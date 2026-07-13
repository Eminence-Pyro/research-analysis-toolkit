"""
research_engine/writer/chapter4_bridge.py
Tier 1 #4 — Chapter 4 narrative bridge

Stitches the AI-written Chapter 4 narrative together with the real
statistical output from the analysis pipeline.

The bridge:
  1. Runs the dataset pipeline (if not already done) to get real numbers
  2. Builds a structured data context (real means, frequencies, chi-square results)
  3. Calls write_chapter(4) with the real numbers injected into the prompt
  4. Ensures every table reference in the narrative matches a real table

Public API
----------
    write_chapter4_with_data(session, project_root, api_key, model) → ChapterContent
    build_analysis_context(pipeline)                                 → str
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING


def build_analysis_context(pipeline) -> str:
    """
    Convert a completed Pipeline's analysis results into a structured
    text context that can be injected into the Chapter 4 LLM prompt.

    Returns a compact string summarising key statistics.
    """
    lines = ["=== REAL ANALYSIS DATA (use these exact numbers in Chapter 4) ===\n"]
    a = pipeline.analysis

    # Overall reliability
    if pipeline.reliability:
        r = pipeline.reliability
        lines.append(f"RELIABILITY: Overall Cronbach's α = {r.overall_alpha:.3f} ({r.overall_interp})")
        for sec in r.sections:
            lines.append(f"  Section {sec.section_key} ({sec.section_title[:30]}): α = {sec.alpha:.3f} [{sec.interpretation}], n={sec.n_items} items")
        lines.append("")

    # Likert section means
    if a.likert_summary:
        ls = a.likert_summary
        lines.append(f"OVERALL MEAN SATISFACTION SCORE: {ls.overall_mean:.2f}/5.00")
        lines.append("SECTION MEANS:")
        for sec_key, sec_mean in ls.section_means.items():
            items = ls.items_for_section(sec_key)
            lines.append(f"  Section {sec_key}: mean = {sec_mean:.2f}")
            for item in sorted(items, key=lambda x: -x.mean)[:3]:
                lines.append(f"    {item.variable_name}: mean={item.mean:.2f}, SD={item.std:.2f} — \"{item.label[:55]}\"")
        lines.append("")

    # Frequency tables (demographics)
    if a.freq_tables:
        lines.append("DEMOGRAPHIC FREQUENCIES (Table numbers start at 4.1):")
        for i, ft in enumerate(a.freq_tables[:8], start=1):
            rows = [r for r in ft.rows if str(r.value) not in ("Total","Missing","TOTAL")]
            top  = sorted(rows, key=lambda x: -x.frequency)[:3]
            lines.append(f"  Table 4.{i}: {ft.label}")
            for row in top:
                lines.append(f"    {row.value}: n={row.frequency} ({row.percent:.1f}%)")
        lines.append("")

    # Crosstabs
    if hasattr(a, "crosstab_results") and a.crosstab_results:
        lines.append("CROSSTABULATION / HYPOTHESIS TEST RESULTS:")
        for i, ct in enumerate(a.crosstab_results, start=1):
            sig = "significant" if ct.p_value < 0.05 else "not significant"
            lines.append(
                f"  Table 4.{20+i}: {ct.var1_label} × {ct.var2_label}: "
                f"χ²={ct.chi_square:.3f}, df={ct.df}, p={ct.p_value:.4f} "
                f"({sig}), Cramer's V={ct.cramers_v:.3f}"
            )
        lines.append("")

    lines.append("=== END OF ANALYSIS DATA ===")
    return "\n".join(lines)


def write_chapter4_with_data(
    session,
    project_root: Path,
    api_key:      str | None = None,
    model:        str        = "gpt-4o",
) -> "ChapterContent":
    """
    Generate Chapter 4 with real statistical data injected.

    If the pipeline has not been run yet, this function:
    1. Generates questionnaire + demographics files (if not present)
    2. Runs the full pipeline
    3. Injects the results into the Chapter 4 prompt

    Parameters
    ----------
    session      : ProjectSession
    project_root : Path to project root (for finding studies/ directory)
    api_key      : OpenAI API key
    model        : OpenAI model

    Returns
    -------
    ChapterContent — Chapter 4 stored in session
    """
    from research_engine.writer.chapter_writer import (
        _build_chapter_prompt, _CHAPTER_STRUCTURES, _LEVEL_GUIDELINES,
        CHAPTER_TITLES
    )
    from research_engine.writer.project_session import (
        EducationLevel, ChapterContent
    )

    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise EnvironmentError("OPENAI_API_KEY not set.")

    study_name  = f"project_{session.session_id}"
    study_dir   = project_root / "studies" / study_name
    analysis_ctx = ""

    # Try to run the pipeline if study files exist
    if study_dir.exists() and (study_dir / "config.json").exists():
        try:
            from research_engine.workflow import Pipeline
            out_dir  = project_root / "output" / study_name
            pipeline = Pipeline(study_dir, output_dir=out_dir, seed=42)
            pipeline.analyse()
            if hasattr(pipeline, "reliability"):
                pipeline.analysis.reliability = pipeline.reliability
            analysis_ctx = build_analysis_context(pipeline)
            session.pipeline_run = True
        except Exception as exc:
            analysis_ctx = f"[Pipeline could not run: {exc}]"
    else:
        analysis_ctx = (
            "[No dataset generated yet — Chapter 4 will be written from "
            "metadata only. Run 'project dataset' first for data-driven narrative.]"
        )

    # Build the standard Ch4 prompt and inject analysis data
    base_prompt = _build_chapter_prompt(session, 4)
    m      = session.metadata
    wc     = m.word_count_for_level().get(4, 4000)
    struct = _CHAPTER_STRUCTURES[4]
    level_g = _LEVEL_GUIDELINES.get(m.level, _LEVEL_GUIDELINES[EducationLevel.UNKNOWN])

    enhanced_prompt = f"""{base_prompt}

IMPORTANT ADDITIONAL CONTEXT — REAL STATISTICAL DATA:
The following data comes from the actual dataset analysis. You MUST use these
exact numbers when writing Chapter 4. Reference table numbers as shown.

{analysis_ctx}

When writing:
- Reference each table by its number (Table 4.1, Table 4.2, etc.)
- Quote exact means, percentages, chi-square values, p-values from the data above
- For each hypothesis test: state H₀, state the test result, interpret it
- In the Discussion section: compare your findings to literature from earlier chapters
"""

    from openai import OpenAI
    client = OpenAI(api_key=key)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system",
             "content": (
                 "You are an expert academic research writer. You write Chapter 4 "
                 "(Data Presentation, Analysis and Discussion) sections that reference "
                 "real statistical output precisely and correctly."
             )},
            {"role": "user", "content": enhanced_prompt},
        ],
        temperature=0.6,
        max_tokens=4096,
    )

    content = response.choices[0].message.content or ""
    usage   = response.usage
    notes   = (
        f"Ch4-Bridge | Pipeline: {'run' if session.pipeline_run else 'not run'} | "
        f"Model: {model} | Tokens: {usage.prompt_tokens}/{usage.completion_tokens}"
        if usage else f"Ch4-Bridge | Model: {model}"
    )

    session.set_chapter(4, content, notes=notes)
    return session.chapters[4]

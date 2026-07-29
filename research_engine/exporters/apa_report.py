"""
research_engine/exporters/apa_report.py
Tier 3 — APA-formatted statistical report generator

Wraps the analysis pipeline output into APA 7th edition formatted
statistical reporting. Produces text blocks ready to paste into
Chapter Four or a standalone results section.

Handles:
  - Descriptive statistics (M, SD)
  - Frequency tables (n, %)
  - Chi-square results with effect sizes
  - Reliability (Cronbach's alpha)
  - Likert item analysis

Public API
----------
    generate_apa_report(pipeline, session=None)  → APAResult
    format_descriptives(analysis)                → str
    format_frequencies(analysis)                 → str
    format_chi_square(analysis)                  → str
    format_reliability(reliability)              → str
    format_likert_summary(analysis)              → str
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class APAResult:
    """Complete APA-formatted statistical report."""
    sections:       dict[str, str] = field(default_factory=dict)
    full_text:      str = ""
    word_count:     int = 0

    def to_text(self) -> str:
        return self.full_text


# ══════════════════════════════════════════════════════════════
# Individual section formatters
# ══════════════════════════════════════════════════════════════

def format_reliability(reliability) -> str:
    """Format Cronbach's alpha results in APA style."""
    lines = ["### Reliability of the Instrument\n"]

    if not reliability:
        return lines[0] + "\n[No reliability data available]\n"

    lines.append(
        f"The internal consistency of the questionnaire was assessed using "
        f"Cronbach's alpha coefficient. The overall reliability of the instrument "
        f"was α = {reliability.overall_alpha:.3f}, which is considered "
        f"{reliability.overall_interp.lower()}. "
    )

    if reliability.sections:
        lines.append("Table 1 shows the reliability coefficients for each section:\n")
        lines.append("| Section | α | Items | Interpretation |")
        lines.append("|---------|---|-------|----------------|")
        for sec in reliability.sections:
            lines.append(
                f"| {sec.section_key}: {sec.section_title[:25]} | "
                f"{sec.alpha:.3f} | {sec.n_items} | {sec.interpretation} |"
            )
        lines.append("")

    return "\n".join(lines)


def format_descriptives(analysis) -> str:
    """Format descriptive statistics in APA style."""
    lines = ["### Descriptive Statistics\n"]

    if not analysis.likert_summary:
        return lines[0] + "\n[No Likert data available]\n"

    ls = analysis.likert_summary
    lines.append(
        f"Descriptive statistics were computed for all Likert-scale items. "
        f"The overall mean satisfaction score was M = {ls.overall_mean:.2f} "
        f"(out of 5.00), indicating that respondents generally "
        f"{'agreed with' if ls.overall_mean >= 3.5 else 'were neutral about' if ls.overall_mean >= 2.5 else 'disagreed with'} "
        f"the statements presented.\n"
    )

    for sec_key, sec_mean in ls.section_means.items():
        items = ls.items_for_section(sec_key)
        if not items:
            continue
        lines.append(f"**Section {sec_key}:** M = {sec_mean:.2f}, SD range: "
                     f"{min(i.std for i in items):.2f}–{max(i.std for i in items):.2f}")
        # Top and bottom items
        sorted_items = sorted(items, key=lambda x: -x.mean)
        if sorted_items:
            top = sorted_items[0]
            lines.append(
                f"  Highest-rated item: \"{top.label[:50]}\" (M = {top.mean:.2f}, SD = {top.std:.2f})"
            )
        if len(sorted_items) > 1:
            bot = sorted_items[-1]
            lines.append(
                f"  Lowest-rated item: \"{bot.label[:50]}\" (M = {bot.mean:.2f}, SD = {bot.std:.2f})"
            )
        lines.append("")

    return "\n".join(lines)


def format_frequencies(analysis) -> str:
    """Format demographic frequency tables in APA style."""
    lines = ["### Demographic Characteristics of Respondents\n"]

    if not analysis.freq_tables:
        return lines[0] + "\n[No frequency data available]\n"

    for i, ft in enumerate(analysis.freq_tables[:8], start=1):
        rows = [r for r in ft.rows if str(r.value) not in ("Total", "Missing", "TOTAL")]
        if not rows:
            continue

        lines.append(f"**Table {i}.** {ft.label}\n")
        lines.append("| Category | n | % |")
        lines.append("|----------|---|---|")

        total_n = sum(r.frequency for r in rows)
        for row in sorted(rows, key=lambda x: -x.frequency):
            lines.append(f"| {row.value} | {row.frequency} | {row.percent:.1f} |")

        lines.append(f"| **Total** | **{total_n}** | **100.0** |\n")

        # APA narrative
        top_row = max(rows, key=lambda x: x.frequency)
        lines.append(
            f"The majority of respondents were in the \"{top_row.value}\" category "
            f"(n = {top_row.frequency}, {top_row.percent:.1f}%).\n"
        )

    return "\n".join(lines)


def format_chi_square(analysis) -> str:
    """Format chi-square / crosstabulation results in APA style."""
    lines = ["### Hypothesis Testing (Chi-Square Analysis)\n"]

    crosstabs = getattr(analysis, "crosstab_results", [])
    if not crosstabs:
        return lines[0] + "\n[No crosstabulation data available]\n"

    for i, ct in enumerate(crosstabs, start=1):
        sig = ct.p_value < 0.05
        sig_text = "statistically significant" if sig else "not statistically significant"

        # APA format: χ²(df, N) = value, p = value, V = value
        lines.append(f"**Hypothesis {i}:**")
        lines.append(
            f"A chi-square test of independence was conducted to examine the "
            f"relationship between {ct.var1_label} and {ct.var2_label}. "
            f"The result was {sig_text}, χ²({ct.df}, N = {getattr(ct, 'n', 'N/A')}) "
            f"= {ct.chi_square:.3f}, p = {ct.p_value:.4f}, Cramer's V = {ct.cramers_v:.3f}."
        )

        if sig:
            lines.append(
                f"  There is a significant association between {ct.var1_label} and "
                f"{ct.var2_label}. The effect size (Cramer's V = {ct.cramers_v:.3f}) "
                f"indicates a "
                f"{'small' if ct.cramers_v < 0.3 else 'medium' if ct.cramers_v < 0.5 else 'large'} "
                f"effect."
            )
        else:
            lines.append(
                f"  There is no significant association between {ct.var1_label} and "
                f"{ct.var2_label}. The null hypothesis is retained."
            )
        lines.append("")

    return "\n".join(lines)


def format_likert_summary(analysis) -> str:
    """Format the Likert section summary in APA style."""
    lines = ["### Summary of Likert-Scale Results\n"]

    if not analysis.likert_summary:
        return lines[0] + "\n[No Likert summary available]\n"

    ls = analysis.likert_summary
    lines.append(
        f"Table 2 presents the mean scores and standard deviations for each "
        f"section of the questionnaire. The overall mean across all sections was "
        f"M = {ls.overall_mean:.2f}.\n"
    )

    lines.append("| Section | M | SD range | Interpretation |")
    lines.append("|---------|---|----------|----------------|")

    for sec_key, sec_mean in ls.section_means.items():
        items = ls.items_for_section(sec_key)
        if not items:
            continue
        sd_range = f"{min(i.std for i in items):.2f}–{max(i.std for i in items):.2f}"
        interp = ("High agreement" if sec_mean >= 4.0
                  else "Moderate agreement" if sec_mean >= 3.0
                  else "Low agreement")
        lines.append(f"| {sec_key} | {sec_mean:.2f} | {sd_range} | {interp} |")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# Full report generator
# ══════════════════════════════════════════════════════════════

def generate_apa_report(
    pipeline,
    session=None,
) -> APAResult:
    """
    Generate a complete APA-formatted statistical report from a
    completed pipeline run.

    Parameters
    ----------
    pipeline : a completed Pipeline object (with .analysis and .reliability)
    session  : optional ProjectSession (for context/titles)

    Returns
    -------
    APAResult — contains sections dict and full_text
    """
    result = APAResult()
    a = pipeline.analysis

    title = "Results"
    if session and session.metadata.title:
        title = f"Results: {session.metadata.title}"

    sections = {}

    # 1. Reliability
    if pipeline.reliability:
        sections["reliability"] = format_reliability(pipeline.reliability)

    # 2. Descriptives
    if a.likert_summary:
        sections["descriptives"] = format_descriptives(a)

    # 3. Frequencies
    if a.freq_tables:
        sections["frequencies"] = format_frequencies(a)

    # 4. Likert summary
    if a.likert_summary:
        sections["likert_summary"] = format_likert_summary(a)

    # 5. Chi-square
    if hasattr(a, "crosstab_results") and a.crosstab_results:
        sections["chi_square"] = format_chi_square(a)

    result.sections = sections
    result.full_text = f"# {title}\n\n" + "\n\n---\n\n".join(sections.values())
    result.word_count = len(result.full_text.split())

    return result

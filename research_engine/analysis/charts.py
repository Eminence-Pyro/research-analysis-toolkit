"""
research_engine/analysis/charts.py
Sprint 1.2 — Chart Engine

Generates publication-ready matplotlib charts from analysis result objects.
All charts use the project's dark/gold visual identity.

Design rules:
  - Functions accept domain result objects, not raw data
  - Every function returns a matplotlib Figure — caller decides save/embed
  - Charts are self-contained (title, labels, legend on the figure)
  - All text is readable at A4 scale

Public API
----------
    likert_bar_chart(likert_summary, section_key)    → Figure
    demographic_pie_chart(freq_table, title)         → Figure
    demographic_bar_chart(freq_table, title)         → Figure
    reliability_bar_chart(reliability_report)        → Figure
    satisfaction_heatmap(dataset, questionnaire)     → Figure
    save_chart(fig, output_dir, stem)                → Path
    all_charts(analysis_bundle, output_dir)          → list[Path]
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import matplotlib
matplotlib.use("Agg")   # headless — no display required
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.figure import Figure

if TYPE_CHECKING:
    from research_engine.analysis.descriptives  import LikertSummary
    from research_engine.analysis.frequencies   import FrequencyTable
    from research_engine.analysis.reliability   import ReliabilityReport
    from research_engine.analysis               import AnalysisBundle   # optional


# ── Project colour palette ────────────────────────────────────
DARK_BG   = "#1a1a2e"
PANEL_BG  = "#16213e"
GOLD      = "#F59E0B"
GOLD_LIGHT= "#FCD34D"
GOLD_DARK = "#D97706"
WHITE     = "#F1F5F9"
GREY_MID  = "#64748B"
GREY_LIGHT= "#94A3B8"
ACCENT    = "#8B5CF6"   # purple accent for contrast

# Likert colour gradient: red → amber → green
LIKERT_PALETTE = ["#EF4444", "#F97316", "#F59E0B", "#22C55E", "#16A34A"]

# Demographic bar palette (cycle if more than 6 categories)
DEMO_PALETTE = [GOLD, ACCENT, "#06B6D4", "#EC4899", "#10B981", "#F97316",
                GOLD_LIGHT, "#8B5CF6", "#3B82F6", "#EF4444"]


def _apply_dark_theme(fig: Figure, ax) -> None:
    """Apply the dark/gold theme to a figure and axis."""
    fig.patch.set_facecolor(DARK_BG)
    if isinstance(ax, np.ndarray):
        axes = ax.flat
    elif hasattr(ax, "__iter__"):
        axes = ax
    else:
        axes = [ax]
    for a in axes:
        a.set_facecolor(PANEL_BG)
        a.tick_params(colors=WHITE, labelsize=9)
        a.xaxis.label.set_color(WHITE)
        a.yaxis.label.set_color(WHITE)
        a.title.set_color(GOLD)
        for spine in a.spines.values():
            spine.set_edgecolor(GREY_MID)


def _wrap(text: str, max_len: int = 32) -> str:
    """Wrap long label text at word boundaries."""
    if len(text) <= max_len:
        return text
    words = text.split()
    lines, current = [], ""
    for w in words:
        if len(current) + len(w) + 1 <= max_len:
            current = (current + " " + w).strip()
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# 1. Likert stacked horizontal bar chart
# ══════════════════════════════════════════════════════════════

def likert_bar_chart(
    likert_summary: "LikertSummary",
    section_key:    str = "",
) -> Figure:
    """
    Horizontal bar chart for one Likert section.
    Items ordered by descending mean.

    Parameters
    ----------
    likert_summary : LikertSummary result object from analysis.descriptives
    section_key    : e.g. "A" — filters items and sets chart title

    Returns
    -------
    matplotlib Figure
    """
    if section_key:
        raw_items = likert_summary.items_for_section(section_key)
    else:
        raw_items = likert_summary.items
    items = sorted(raw_items, key=lambda x: x.mean, reverse=True)
    labels  = [_wrap(item.label, 30) for item in items]
    means   = [item.mean for item in items]
    n_items = len(items)

    fig, ax = plt.subplots(figsize=(11, max(4, n_items * 0.7 + 1.5)))
    _apply_dark_theme(fig, ax)

    y_pos = np.arange(n_items)
    bars  = ax.barh(y_pos, means, color=GOLD, alpha=0.85,
                    edgecolor=GOLD_DARK, linewidth=0.6, height=0.6)

    # Add value labels
    for bar, mean in zip(bars, means):
        ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2,
                f"{mean:.2f}", va="center", ha="left",
                color=GOLD_LIGHT, fontsize=8.5, fontweight="bold")

    # Scale line at neutral (3.0)
    ax.axvline(x=3.0, color=GREY_MID, linewidth=1.2, linestyle="--", alpha=0.7,
               label="Neutral (3.0)")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, color=WHITE, fontsize=8.5)
    ax.set_xlim(1, 5.6)
    ax.set_xlabel("Mean Score (1 = Very Dissatisfied, 5 = Very Satisfied)",
                  color=GREY_LIGHT, fontsize=9)
    title = f"Section {section_key}: Mean Satisfaction Scores" if section_key \
            else "Mean Satisfaction Scores"
    ax.set_title(title, color=GOLD, fontsize=12, fontweight="bold", pad=14)
    ax.legend(facecolor=PANEL_BG, edgecolor=GREY_MID,
              labelcolor=WHITE, fontsize=8)
    ax.invert_yaxis()

    fig.tight_layout(pad=1.8)
    return fig


# ══════════════════════════════════════════════════════════════
# 2. Demographic pie chart
# ══════════════════════════════════════════════════════════════

def demographic_pie_chart(
    freq_table: "FrequencyTable",
    title:      str = "",
) -> Figure:
    """
    Pie chart for a categorical demographic variable.
    Slices with < 5% are grouped into 'Other'.
    """
    rows   = [r for r in freq_table.rows if str(r.value) not in ("Total", "Missing", "TOTAL")]
    labels = [_wrap(str(r.value), 20) for r in rows]
    values = [r.frequency for r in rows]
    total  = sum(values)
    if total == 0:
        return plt.figure()

    # Group tiny slices
    threshold = 0.05 * total
    big_labels, big_vals = [], []
    other_val = 0
    for lbl, val in zip(labels, values):
        if val >= threshold:
            big_labels.append(lbl)
            big_vals.append(val)
        else:
            other_val += val
    if other_val:
        big_labels.append("Other")
        big_vals.append(other_val)

    colours = DEMO_PALETTE[: len(big_vals)]

    fig, ax = plt.subplots(figsize=(7, 5.5))
    _apply_dark_theme(fig, ax)

    wedges, texts, autotexts = ax.pie(
        big_vals,
        labels=None,
        colors=colours,
        autopct="%1.1f%%",
        startangle=140,
        pctdistance=0.78,
        wedgeprops={"edgecolor": DARK_BG, "linewidth": 1.5},
    )
    for at in autotexts:
        at.set_color(DARK_BG)
        at.set_fontsize(8)
        at.set_fontweight("bold")

    ax.legend(wedges, big_labels, loc="lower center",
              bbox_to_anchor=(0.5, -0.12), ncol=3,
              facecolor=PANEL_BG, edgecolor=GREY_MID,
              labelcolor=WHITE, fontsize=8)
    ax.set_title(title or freq_table.label,
                 color=GOLD, fontsize=12, fontweight="bold", pad=16)

    fig.tight_layout(pad=1.5)
    return fig


# ══════════════════════════════════════════════════════════════
# 3. Demographic bar chart
# ══════════════════════════════════════════════════════════════

def demographic_bar_chart(
    freq_table: "FrequencyTable",
    title:      str = "",
) -> Figure:
    """
    Vertical bar chart for a categorical demographic variable.
    Better than a pie when there are more than 5 categories.
    """
    rows    = [r for r in freq_table.rows if str(r.value) not in ("Total", "Missing", "TOTAL")]
    labels  = [_wrap(str(r.value), 18) for r in rows]
    values  = [r.frequency for r in rows]
    percents= [r.percent for r in rows]
    n       = len(labels)
    colours = (DEMO_PALETTE * ((n // len(DEMO_PALETTE)) + 1))[:n]

    fig, ax = plt.subplots(figsize=(max(6, n * 1.1 + 1.5), 5.5))
    _apply_dark_theme(fig, ax)

    x_pos = np.arange(n)
    bars  = ax.bar(x_pos, values, color=colours, edgecolor=DARK_BG,
                   linewidth=0.7, width=0.6, alpha=0.9)

    for bar, pct in zip(bars, percents):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(values) * 0.015,
                f"{pct:.1f}%", ha="center", va="bottom",
                color=GOLD_LIGHT, fontsize=8, fontweight="bold")

    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels, rotation=30, ha="right", color=WHITE, fontsize=8.5)
    ax.set_ylabel("Frequency (n)", color=GREY_LIGHT, fontsize=9)
    ax.set_title(title or freq_table.label,
                 color=GOLD, fontsize=12, fontweight="bold", pad=14)
    ax.set_xlim(-0.5, n - 0.5)
    ax.set_ylim(0, max(values) * 1.15)

    fig.tight_layout(pad=1.8)
    return fig


# ══════════════════════════════════════════════════════════════
# 4. Reliability bar chart (Cronbach's alpha per section)
# ══════════════════════════════════════════════════════════════

def reliability_bar_chart(
    reliability_report: "ReliabilityReport",
) -> Figure:
    """
    Horizontal bar chart of Cronbach's alpha per section,
    with colour-coded interpretation thresholds.
    """
    sections = [s for s in reliability_report.sections if s.alpha == s.alpha]
    if not sections:
        return plt.figure()

    labels = [f"Section {s.section_key}: {s.section_title[:28]}" for s in sections]
    alphas = [s.alpha for s in sections]

    def _colour(a):
        if a >= 0.8: return "#22C55E"  # green
        if a >= 0.7: return GOLD       # gold
        if a >= 0.6: return "#F97316"  # orange
        return "#EF4444"               # red

    colours = [_colour(a) for a in alphas]
    n = len(labels)

    fig, ax = plt.subplots(figsize=(10, max(3.5, n * 0.7 + 2)))
    _apply_dark_theme(fig, ax)

    y_pos = np.arange(n)
    bars  = ax.barh(y_pos, alphas, color=colours, edgecolor=DARK_BG,
                    linewidth=0.5, height=0.55, alpha=0.9)

    for bar, alpha_val, sec in zip(bars, alphas, sections):
        ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
                f"α={alpha_val:.3f}  [{sec.interpretation}]",
                va="center", ha="left", color=WHITE, fontsize=8.5)

    # Threshold reference lines
    for threshold, label_str in [(0.9, "Excellent"), (0.8, "Good"),
                                  (0.7, "Acceptable"), (0.6, "Questionable")]:
        ax.axvline(x=threshold, color=GREY_MID, linewidth=0.9,
                   linestyle="--", alpha=0.5)
        ax.text(threshold + 0.002, n - 0.1, label_str,
                color=GREY_LIGHT, fontsize=7, rotation=90, va="top")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, color=WHITE, fontsize=8.5)
    ax.set_xlim(0, 1.18)
    ax.set_xlabel("Cronbach's Alpha (α)", color=GREY_LIGHT, fontsize=9)
    ax.set_title("Internal Consistency — Cronbach's Alpha by Section",
                 color=GOLD, fontsize=12, fontweight="bold", pad=14)
    ax.invert_yaxis()

    # Colour legend
    legend_patches = [
        mpatches.Patch(color="#22C55E", label="Good–Excellent (≥0.8)"),
        mpatches.Patch(color=GOLD,      label="Acceptable (0.7–0.8)"),
        mpatches.Patch(color="#F97316", label="Questionable (0.6–0.7)"),
        mpatches.Patch(color="#EF4444", label="Poor (<0.6)"),
    ]
    ax.legend(handles=legend_patches, loc="lower right",
              facecolor=PANEL_BG, edgecolor=GREY_MID,
              labelcolor=WHITE, fontsize=7.5)

    fig.tight_layout(pad=1.8)
    return fig


# ══════════════════════════════════════════════════════════════
# 5. Satisfaction heatmap (section means × facility)
# ══════════════════════════════════════════════════════════════

def satisfaction_heatmap(
    dataset,
    questionnaire,
) -> Figure:
    """
    Heatmap of mean satisfaction scores: sections (rows) × facilities (columns).
    Shows which facilities score higher/lower on each dimension.
    """
    import warnings

    sections    = [s for s in questionnaire.sections
                   if any(q.question_type.value in ("likert_5","likert_4")
                          for q in s.questions)]
    facilities  = sorted({r.facility_id for r in dataset._respondents.values()
                          if r.facility_id is not None})
    if not sections or not facilities:
        return plt.figure()

    section_labels  = [f"Sec {s.key}" for s in sections]
    facility_labels = [f"Fac {f}" for f in facilities]

    data_matrix = np.full((len(sections), len(facilities)), np.nan)

    for si, sec in enumerate(sections):
        likert_vars = [q.variable_name for q in sec.questions
                       if q.question_type.value in ("likert_5", "likert_4")]
        for fi, fac_id in enumerate(facilities):
            vals = []
            for r in dataset._respondents.values():
                if r.facility_id != fac_id:
                    continue
                for vname in likert_vars:
                    v = r.get_response(vname)
                    if v is not None and isinstance(v, (int, float)):
                        vals.append(float(v))
            if vals:
                data_matrix[si, fi] = np.mean(vals)

    fig, ax = plt.subplots(figsize=(max(6, len(facilities) * 1.6 + 2.5),
                                     max(4, len(sections) * 0.85 + 2)))
    _apply_dark_theme(fig, ax)

    import matplotlib.colors as mcolors
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "rat_heatmap",
        ["#EF4444", "#F97316", "#F59E0B", "#22C55E"],
        N=256,
    )
    im = ax.imshow(data_matrix, cmap=cmap, aspect="auto",
                   vmin=1, vmax=5, interpolation="nearest")

    ax.set_xticks(range(len(facility_labels)))
    ax.set_xticklabels(facility_labels, color=WHITE, fontsize=9)
    ax.set_yticks(range(len(section_labels)))
    ax.set_yticklabels(section_labels, color=WHITE, fontsize=9)

    # Annotate cells
    for si in range(len(sections)):
        for fi in range(len(facilities)):
            val = data_matrix[si, fi]
            if not np.isnan(val):
                ax.text(fi, si, f"{val:.2f}", ha="center", va="center",
                        color=DARK_BG, fontsize=9, fontweight="bold")

    cbar = fig.colorbar(im, ax=ax, orientation="vertical", pad=0.02)
    cbar.ax.yaxis.set_tick_params(color=WHITE)
    cbar.set_ticks([1, 2, 3, 4, 5])
    cbar.ax.set_yticklabels(["1", "2", "3", "4", "5"], color=WHITE, fontsize=8)
    cbar.set_label("Mean Satisfaction Score", color=GREY_LIGHT, fontsize=9)

    ax.set_title("Mean Satisfaction by Section and Facility",
                 color=GOLD, fontsize=12, fontweight="bold", pad=14)
    fig.tight_layout(pad=1.8)
    return fig


# ══════════════════════════════════════════════════════════════
# Utility: save + batch generation
# ══════════════════════════════════════════════════════════════

def save_chart(fig: Figure, output_dir: str | Path, stem: str) -> Path:
    """Save a figure as PNG (300 dpi) and return the file path."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{stem}.png"
    fig.savefig(str(path), dpi=300, bbox_inches="tight",
                facecolor=DARK_BG, edgecolor="none")
    plt.close(fig)
    return path


def all_charts(analysis_bundle, output_dir: str | Path) -> list[Path]:
    """
    Generate all standard charts for an analysis bundle and save to output_dir.

    Parameters
    ----------
    analysis_bundle : the AnalysisBundle from Pipeline.analysis
                      (needs .likert_summary, .freq_tables, .reliability)
    output_dir      : directory to save PNG files

    Returns
    -------
    list[Path] — paths of all saved chart files
    """
    output_dir = Path(output_dir) / "charts"
    paths: list[Path] = []

    # 1. Likert bar charts — one per section
    if hasattr(analysis_bundle, "likert_summary") and analysis_bundle.likert_summary:
        ls = analysis_bundle.likert_summary
        sec_keys = list(dict.fromkeys(item.section_key for item in ls.items))
        for sec_key in sec_keys:
            fig  = likert_bar_chart(ls, section_key=sec_key)
            path = save_chart(fig, output_dir, f"likert_section_{sec_key.lower()}")
            paths.append(path)

    # 2. Demographic charts (bar for variables with >5 categories, pie otherwise)
    if hasattr(analysis_bundle, "freq_tables") and analysis_bundle.freq_tables:
        for ft in analysis_bundle.freq_tables:
            n_cats = len([r for r in ft.rows if str(r.value) not in ("Total","Missing","TOTAL")])
            if n_cats == 0:
                continue
            if n_cats > 5:
                fig = demographic_bar_chart(ft, title=ft.label)
            else:
                fig = demographic_pie_chart(ft, title=ft.label)
            stem = "demo_" + ft.variable_name.lower().replace(" ", "_")
            paths.append(save_chart(fig, output_dir, stem))

    # 3. Reliability bar chart
    if hasattr(analysis_bundle, "reliability") and analysis_bundle.reliability:
        fig  = reliability_bar_chart(analysis_bundle.reliability)
        paths.append(save_chart(fig, output_dir, "reliability_alpha"))

    return paths

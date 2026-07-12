"""
research_engine/analysis/reliability.py
Milestone 1.1.B — Reliability Analysis

Cronbach's alpha internal consistency coefficient for multi-item
Likert scales, grouped by questionnaire section.

Cronbach's alpha measures how closely related a set of items is as
a group — i.e., whether they all measure the same underlying construct.

    α = (k / (k-1)) × (1 − Σσ²ᵢ / σ²_total)

where k = number of items, σ²ᵢ = variance of item i,
      σ²_total = variance of the sum of all items.

Interpretation (Nunnally & Bernstein, 1994; George & Mallery, 2003):
    α ≥ 0.9  → Excellent
    α ≥ 0.8  → Good
    α ≥ 0.7  → Acceptable
    α ≥ 0.6  → Questionable
    α ≥ 0.5  → Poor
    α <  0.5  → Unacceptable

Public API
----------
    cronbach_alpha(matrix)                → float
    item_total_correlations(matrix)       → list[float]
    alpha_if_item_deleted(matrix)         → list[float]
    section_reliability(dataset, section) → SectionReliability
    full_reliability(dataset, questionnaire) → ReliabilityReport
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import numpy as np

from research_engine.models import Dataset, Questionnaire


# ══════════════════════════════════════════════════════════════
# Core statistical functions
# (Accept plain numpy arrays — testable with no domain objects)
# ══════════════════════════════════════════════════════════════

def cronbach_alpha(matrix: np.ndarray) -> float:
    """
    Compute Cronbach's alpha for a 2-D item matrix.

    Parameters
    ----------
    matrix : np.ndarray, shape (n_respondents, n_items)
        Each column is one Likert item; each row is one respondent.
        Must have at least 2 items and 2 respondents.

    Returns
    -------
    float — Cronbach's alpha, in the range (−∞, 1.0].
            Returns nan if the matrix is degenerate (zero total variance).
    """
    n_resp, k = matrix.shape
    if k < 2 or n_resp < 2:
        return float("nan")

    item_vars = np.var(matrix, axis=0, ddof=1)   # variance per item
    total_var = np.var(matrix.sum(axis=1), ddof=1)  # variance of row sums

    if total_var == 0.0:
        return float("nan")

    alpha = (k / (k - 1)) * (1.0 - item_vars.sum() / total_var)
    return float(alpha)


def item_total_correlations(matrix: np.ndarray) -> list[float]:
    """
    Pearson correlation between each item and the rest-score
    (sum of all other items), also called corrected item-total correlation.

    The rest-score excludes the item itself to avoid spurious inflation.

    Parameters
    ----------
    matrix : np.ndarray, shape (n_respondents, n_items)

    Returns
    -------
    list[float] — one correlation per item, in column order.
                  nan if an item or rest-score has zero variance.
    """
    _, k = matrix.shape
    row_sums = matrix.sum(axis=1)
    correlations: list[float] = []

    for i in range(k):
        item      = matrix[:, i]
        rest      = row_sums - item          # rest-score (all others)
        item_std  = np.std(item, ddof=1)
        rest_std  = np.std(rest, ddof=1)

        if item_std == 0.0 or rest_std == 0.0:
            correlations.append(float("nan"))
            continue

        # Pearson r
        cov = np.mean((item - item.mean()) * (rest - rest.mean()))
        r   = cov / (item_std * rest_std)
        correlations.append(float(r))

    return correlations


def alpha_if_item_deleted(matrix: np.ndarray) -> list[float]:
    """
    Cronbach's alpha if each item is removed from the scale.

    Useful for identifying items that reduce overall reliability.
    An item whose deletion increases alpha is a candidate for removal.

    Parameters
    ----------
    matrix : np.ndarray, shape (n_respondents, n_items)

    Returns
    -------
    list[float] — alpha-if-deleted for each item, in column order.
    """
    _, k = matrix.shape
    alphas: list[float] = []

    for i in range(k):
        # Build reduced matrix by dropping column i
        reduced = np.delete(matrix, i, axis=1)
        alphas.append(cronbach_alpha(reduced))

    return alphas


# ══════════════════════════════════════════════════════════════
# Interpretation helpers
# ══════════════════════════════════════════════════════════════

def _interpret_alpha(alpha: float) -> str:
    """Verbal interpretation of a Cronbach's alpha value."""
    if np.isnan(alpha):
        return "Cannot compute"
    if alpha >= 0.9:
        return "Excellent"
    if alpha >= 0.8:
        return "Good"
    if alpha >= 0.7:
        return "Acceptable"
    if alpha >= 0.6:
        return "Questionable"
    if alpha >= 0.5:
        return "Poor"
    return "Unacceptable"


def _interpret_item_total(r: float) -> str:
    """Verbal flag for an item-total correlation."""
    if np.isnan(r):
        return "Cannot compute"
    if r >= 0.5:
        return "Strong"
    if r >= 0.3:
        return "Acceptable"
    if r >= 0.2:
        return "Weak"
    return "Very weak — consider removing"


# ══════════════════════════════════════════════════════════════
# Result objects
# ══════════════════════════════════════════════════════════════

@dataclass
class ItemReliability:
    """
    Reliability statistics for one Likert item within a section.

    Attributes
    ----------
    variable_name       : column name in the dataset
    question_number     : e.g. "A1"
    label               : question text
    mean                : item mean
    std                 : item standard deviation
    item_total_r        : corrected item-total correlation
    item_total_interp   : "Strong" / "Acceptable" / "Weak" / "Very weak..."
    alpha_if_deleted    : Cronbach's alpha if this item is dropped
    """
    variable_name:     str
    question_number:   str
    label:             str
    mean:              float
    std:               float
    item_total_r:      float
    item_total_interp: str
    alpha_if_deleted:  float

    def to_row(self) -> tuple:
        """Flat tuple for export: (No., Statement, Mean, SD, r, r-interp, α-if-del)"""
        return (
            self.question_number,
            self.label,
            round(self.mean, 3),
            round(self.std, 3),
            round(self.item_total_r, 3) if not np.isnan(self.item_total_r) else "–",
            self.item_total_interp,
            round(self.alpha_if_deleted, 3) if not np.isnan(self.alpha_if_deleted) else "–",
        )


@dataclass
class SectionReliability:
    """
    Cronbach's alpha and item-level statistics for one questionnaire section.

    Attributes
    ----------
    section_key    : "A", "B", …
    section_title  : human-readable section name
    n_items        : number of Likert items in the section
    n_respondents  : number of valid respondents
    alpha          : Cronbach's alpha for the section
    interpretation : verbal interpretation of alpha
    items          : list[ItemReliability] — one per Likert item
    """
    section_key:    str
    section_title:  str
    n_items:        int
    n_respondents:  int
    alpha:          float
    interpretation: str
    items:          list[ItemReliability] = field(default_factory=list)

    def to_summary_row(self) -> tuple:
        """Flat tuple: (Section, Title, N items, N respondents, α, Interpretation)"""
        a = round(self.alpha, 3) if not np.isnan(self.alpha) else "–"
        return (
            f"Section {self.section_key}",
            self.section_title,
            self.n_items,
            self.n_respondents,
            a,
            self.interpretation,
        )

    def __repr__(self) -> str:
        a = f"{self.alpha:.3f}" if not np.isnan(self.alpha) else "nan"
        return (
            f"SectionReliability(section={self.section_key!r}, "
            f"k={self.n_items}, α={a}, [{self.interpretation}])"
        )


@dataclass
class ReliabilityReport:
    """
    Cronbach's alpha for all sections in the questionnaire.

    Attributes
    ----------
    sections          : list[SectionReliability] — one per section
    overall_alpha     : alpha computed across all items in all sections
    overall_interp    : verbal interpretation of overall_alpha
    """
    sections:       list[SectionReliability]
    overall_alpha:  float
    overall_interp: str

    def to_summary_rows(self) -> list[tuple]:
        """All section rows + overall row, for the Excel/Word summary table."""
        rows = [s.to_summary_row() for s in self.sections]
        a    = round(self.overall_alpha, 3) if not np.isnan(self.overall_alpha) else "–"
        rows.append(("Overall", "All sections combined",
                     sum(s.n_items for s in self.sections),
                     self.sections[0].n_respondents if self.sections else 0,
                     a, self.overall_interp))
        return rows

    def __repr__(self) -> str:
        a = f"{self.overall_alpha:.3f}" if not np.isnan(self.overall_alpha) else "nan"
        return (
            f"ReliabilityReport(sections={len(self.sections)}, "
            f"overall_α={a}, [{self.overall_interp}])"
        )


# ══════════════════════════════════════════════════════════════
# Public high-level API
# ══════════════════════════════════════════════════════════════

def section_reliability(
    dataset:      Dataset,
    section:      Any,          # Section object from questionnaire
) -> SectionReliability:
    """
    Compute Cronbach's alpha and item statistics for one questionnaire section.

    Only items with QuestionType LIKERT_5 or LIKERT_4 are included.
    Items with zero variance are excluded from alpha computation with a warning.

    Parameters
    ----------
    dataset  : the generated Dataset
    section  : a Section object (from questionnaire.sections)

    Returns
    -------
    SectionReliability
    """
    # Collect Likert items from the section
    likert_items = [
        q for q in section.questions
        if q.question_type.value in ("likert_5", "likert_4")
    ]

    if not likert_items:
        return SectionReliability(
            section_key   = section.key,
            section_title = section.title,
            n_items       = 0,
            n_respondents = len(dataset),
            alpha         = float("nan"),
            interpretation= "No Likert items",
            items         = [],
        )

    # Build item matrix — rows = respondents, cols = items
    col_data: list[list[float]] = []
    valid_items = []
    for q in likert_items:
        vals = [
            float(v) for v in dataset.column_values(q.variable_name)
            if v is not None and isinstance(v, (int, float))
        ]
        if len(vals) >= 2 and np.std(vals, ddof=1) > 0:
            col_data.append(vals)
            valid_items.append(q)

    if len(col_data) < 2:
        return SectionReliability(
            section_key   = section.key,
            section_title = section.title,
            n_items       = len(likert_items),
            n_respondents = len(dataset),
            alpha         = float("nan"),
            interpretation= "Insufficient variance",
            items         = [],
        )

    # Align lengths (take minimum to handle any missing)
    min_n  = min(len(c) for c in col_data)
    matrix = np.array([c[:min_n] for c in col_data]).T   # (n, k)

    # Core statistics
    alpha    = cronbach_alpha(matrix)
    itc      = item_total_correlations(matrix)
    aid      = alpha_if_item_deleted(matrix)
    col_means= matrix.mean(axis=0)
    col_stds = matrix.std(axis=0, ddof=1)

    item_stats: list[ItemReliability] = []
    for i, q in enumerate(valid_items):
        item_stats.append(ItemReliability(
            variable_name     = q.variable_name,
            question_number   = q.number,
            label             = q.text,
            mean              = float(col_means[i]),
            std               = float(col_stds[i]),
            item_total_r      = itc[i],
            item_total_interp = _interpret_item_total(itc[i]),
            alpha_if_deleted  = aid[i],
        ))

    return SectionReliability(
        section_key   = section.key,
        section_title = section.title,
        n_items       = len(valid_items),
        n_respondents = min_n,
        alpha         = alpha,
        interpretation= _interpret_alpha(alpha),
        items         = item_stats,
    )


def full_reliability(
    dataset:       Dataset,
    questionnaire: Questionnaire,
) -> ReliabilityReport:
    """
    Compute Cronbach's alpha for every section in the questionnaire,
    plus an overall alpha across all sections combined.

    Parameters
    ----------
    dataset        : the generated Dataset
    questionnaire  : the Questionnaire (provides section and item structure)

    Returns
    -------
    ReliabilityReport
    """
    section_results: list[SectionReliability] = []

    for sec in questionnaire.sections:
        sr = section_reliability(dataset, sec)
        section_results.append(sr)

    # Overall alpha — across all Likert items in all sections
    all_items: list[str] = []
    for sec in questionnaire.sections:
        all_items.extend(
            q.variable_name for q in sec.questions
            if q.question_type.value in ("likert_5", "likert_4")
        )

    col_data = []
    for varname in all_items:
        vals = [
            float(v) for v in dataset.column_values(varname)
            if v is not None and isinstance(v, (int, float))
        ]
        if len(vals) >= 2 and np.std(vals, ddof=1) > 0:
            col_data.append(vals)

    if len(col_data) >= 2:
        min_n         = min(len(c) for c in col_data)
        overall_matrix= np.array([c[:min_n] for c in col_data]).T
        overall_alpha = cronbach_alpha(overall_matrix)
    else:
        overall_alpha = float("nan")

    return ReliabilityReport(
        sections      = section_results,
        overall_alpha = overall_alpha,
        overall_interp= _interpret_alpha(overall_alpha),
    )

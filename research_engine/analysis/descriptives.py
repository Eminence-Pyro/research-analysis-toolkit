"""
research_engine/analysis/descriptives.py
Stage 9 — Analysis Engine

Descriptive statistics for numeric (Scale) variables — and Likert items
treated as interval data (common in health research).

Public API
----------
    describe(dataset, variable_name)          → DescriptiveStats
    describe_many(dataset, variable_names)    → list[DescriptiveStats]
    likert_summary(dataset, questionnaire)    → LikertSummary
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import numpy as np

from research_engine.models import Dataset, Questionnaire


# ── Result objects ────────────────────────────────────────────

@dataclass
class DescriptiveStats:
    """
    Descriptive statistics for one numeric variable.

    All statistics are computed on non-missing values only.
    """
    variable_name: str
    label:         str
    n:             int
    mean:          float
    std:           float
    minimum:       float
    q1:            float
    median:        float
    q3:            float
    maximum:       float
    skewness:      float
    kurtosis:      float
    missing:       int = 0

    def to_row(self) -> tuple:
        """Return a flat tuple for export: (label, n, mean, SD, min, median, max, skew)"""
        return (
            self.label, self.n,
            round(self.mean, 3), round(self.std, 3),
            round(self.minimum, 2), round(self.median, 3),
            round(self.maximum, 2), round(self.skewness, 3),
        )

    def __repr__(self) -> str:
        return (
            f"DescriptiveStats({self.variable_name!r}, "
            f"n={self.n}, mean={self.mean:.3f}, sd={self.std:.3f})"
        )


@dataclass
class LikertItemStats:
    """Descriptive statistics for one Likert item, plus label/number."""
    section_key:   str
    question_number: str
    variable_name: str
    label:         str
    n:             int
    mean:          float
    std:           float
    interpretation: str   # "Very Dissatisfied" … "Very Satisfied"

    def to_row(self) -> tuple:
        return (
            self.question_number, self.label, self.n,
            round(self.mean, 3), round(self.std, 3), self.interpretation,
        )


@dataclass
class LikertSummary:
    """
    Descriptive statistics for all Likert items in the questionnaire,
    grouped by section.

    Used to produce the core Chapter Four table:
    "Table X: Respondents' Mean Scores on [Construct], by Item"
    """
    items:          list[LikertItemStats]
    section_means:  dict[str, float]   # {section_key: mean}
    overall_mean:   float

    def items_for_section(self, key: str) -> list[LikertItemStats]:
        return [item for item in self.items if item.section_key == key]

    def to_rows(self) -> list[tuple]:
        return [item.to_row() for item in self.items]

    def __repr__(self) -> str:
        return (
            f"LikertSummary(items={len(self.items)}, "
            f"overall_mean={self.overall_mean:.3f})"
        )


# ── Public API ────────────────────────────────────────────────

def describe(
    dataset:       Dataset,
    variable_name: str,
    label:         str = "",
) -> DescriptiveStats | None:
    """
    Compute descriptive statistics for one numeric variable.

    Returns None if the variable has no valid numeric values.
    """
    values = [
        float(v) for v in dataset.column_values(variable_name)
        if v is not None and isinstance(v, (int, float)) and not isinstance(v, bool)
    ]
    if not values:
        return None

    arr     = np.array(values)
    n_total = len(dataset.respondents) if hasattr(dataset, "respondents") else len(dataset)
    missing = n_total - len(values)

    return DescriptiveStats(
        variable_name = variable_name,
        label         = label or variable_name.replace("_", " ").title(),
        n             = len(arr),
        mean          = float(np.mean(arr)),
        std           = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
        minimum       = float(np.min(arr)),
        q1            = float(np.percentile(arr, 25)),
        median        = float(np.median(arr)),
        q3            = float(np.percentile(arr, 75)),
        maximum       = float(np.max(arr)),
        skewness      = float(_skewness(arr)),
        kurtosis      = float(_kurtosis(arr)),
        missing       = missing,
    )


def describe_many(
    dataset:        Dataset,
    variable_names: list[str],
    labels:         dict[str, str] | None = None,
) -> list[DescriptiveStats]:
    """
    Compute descriptive statistics for multiple numeric variables.

    Skips variables with no valid numeric values (returns only non-None results).
    """
    labels = labels or {}
    results = []
    for name in variable_names:
        stat = describe(dataset, name, label=labels.get(name, ""))
        if stat is not None:
            results.append(stat)
    return results


def likert_summary(
    dataset:      Dataset,
    questionnaire: Questionnaire,
    labels:        dict[str, str] | None = None,
) -> LikertSummary:
    """
    Compute mean and SD for every Likert item in the questionnaire,
    grouped by section.

    This is the primary Chapter Four table function.

    Parameters
    ----------
    dataset        : the generated/imported Dataset
    questionnaire  : the Questionnaire (provides section/item structure)
    labels         : optional {variable_name: label} overrides

    Returns
    -------
    LikertSummary with per-item stats and section/overall means
    """
    labels    = labels or {}
    items:    list[LikertItemStats] = []
    sec_means: dict[str, float]     = {}

    for section in questionnaire.sections:
        section_values: list[float] = []

        for question in section.questions:
            vname  = question.variable_name
            values = dataset.likert_column(vname)
            if not values:
                continue

            arr  = np.array(values, dtype=float)
            mean = float(np.mean(arr))
            std  = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
            section_values.extend(values)

            items.append(LikertItemStats(
                section_key      = section.key,
                question_number  = question.number,
                variable_name    = vname,
                label            = labels.get(vname, question.text),
                n                = len(values),
                mean             = round(mean, 3),
                std              = round(std, 3),
                interpretation   = _likert_label(mean),
            ))

        if section_values:
            sec_means[section.key] = round(float(np.mean(section_values)), 3)

    all_means = list(sec_means.values())
    overall   = round(float(np.mean(all_means)), 3) if all_means else 0.0

    return LikertSummary(
        items         = items,
        section_means = sec_means,
        overall_mean  = overall,
    )


# ── Helpers ───────────────────────────────────────────────────

def _skewness(arr: np.ndarray) -> float:
    n = len(arr)
    if n < 3:
        return 0.0
    mean = np.mean(arr)
    std  = np.std(arr, ddof=1)
    if std == 0:
        return 0.0
    return float(np.mean(((arr - mean) / std) ** 3))


def _kurtosis(arr: np.ndarray) -> float:
    n = len(arr)
    if n < 4:
        return 0.0
    mean = np.mean(arr)
    std  = np.std(arr, ddof=1)
    if std == 0:
        return 0.0
    return float(np.mean(((arr - mean) / std) ** 4) - 3)   # excess kurtosis


def _likert_label(mean: float) -> str:
    """Convert a Likert mean to a verbal interpretation."""
    if mean >= 4.5: return "Very Satisfied / Strongly Agree"
    if mean >= 3.5: return "Satisfied / Agree"
    if mean >= 2.5: return "Neutral / Undecided"
    if mean >= 1.5: return "Dissatisfied / Disagree"
    return "Very Dissatisfied / Strongly Disagree"

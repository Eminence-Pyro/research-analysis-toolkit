"""
research_engine/analysis/crosstabs.py
Stage 9 — Analysis Engine

Cross-tabulation tables with chi-square test and Cramer's V.

Commonly used in health research to examine associations between
demographic variables and satisfaction categories —
e.g. "Is there a significant association between education level
and satisfaction category?"

Public API
----------
    crosstab(dataset, row_var, col_var)  → CrosstabResult
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import numpy as np

from research_engine.models import Dataset


# ── Result objects ────────────────────────────────────────────

@dataclass
class CrosstabResult:
    """
    A cross-tabulation of two categorical variables.

    Attributes
    ----------
    row_variable    : the row variable name (e.g. "education")
    col_variable    : the column variable name (e.g. "satisfaction_category")
    row_label       : human-readable row label
    col_label       : human-readable column label
    row_categories  : ordered list of row categories
    col_categories  : ordered list of column categories
    observed        : 2D list — observed[row_idx][col_idx] = count
    row_totals      : total per row category
    col_totals      : total per column category
    n               : total number of observations
    chi2            : chi-square statistic
    p_value         : p-value for chi-square test
    df              : degrees of freedom
    cramers_v       : Cramer's V (effect size, 0–1)
    significant     : True if p_value < 0.05
    note            : warning if expected cell counts < 5
    """
    row_variable:   str
    col_variable:   str
    row_label:      str
    col_label:      str
    row_categories: list[Any]
    col_categories: list[Any]
    observed:       list[list[int]]
    row_totals:     list[int]
    col_totals:     list[int]
    n:              int
    chi2:           float
    p_value:        float
    df:             int
    cramers_v:      float
    significant:    bool
    note:           str = ""

    def to_rows(self) -> list[tuple]:
        """
        Return the crosstab as a list of tuples for export.
        First row is the header. Last rows include column totals.
        """
        header = ("",) + tuple(str(c) for c in self.col_categories) + ("Total",)
        rows   = [header]
        for i, row_cat in enumerate(self.row_categories):
            row = (str(row_cat),) + tuple(self.observed[i]) + (self.row_totals[i],)
            rows.append(row)
        total_row = ("Total",) + tuple(self.col_totals) + (self.n,)
        rows.append(total_row)
        return rows

    def stats_row(self) -> tuple:
        """Return (chi2, df, p_value, cramers_v, significant) as a tuple."""
        sig = "Yes (p < 0.05)" if self.significant else "No (p ≥ 0.05)"
        return (
            round(self.chi2, 3), self.df,
            round(self.p_value, 4), round(self.cramers_v, 3), sig,
        )

    def __repr__(self) -> str:
        return (
            f"CrosstabResult({self.row_variable!r} × {self.col_variable!r}, "
            f"χ²={self.chi2:.3f}, p={self.p_value:.4f}, V={self.cramers_v:.3f})"
        )


# ── Public API ────────────────────────────────────────────────

def crosstab(
    dataset:      Dataset,
    row_variable: str,
    col_variable: str,
    row_label:    str = "",
    col_label:    str = "",
    row_order:    list | None = None,
    col_order:    list | None = None,
) -> CrosstabResult:
    """
    Compute a cross-tabulation of two categorical variables with chi-square.

    Parameters
    ----------
    dataset      : the Dataset
    row_variable : variable name for rows (e.g. "education")
    col_variable : variable name for columns (e.g. "satisfaction_category")
    row_label    : human-readable row label
    col_label    : human-readable column label
    row_order    : optional explicit ordering for row categories
    col_order    : optional explicit ordering for column categories

    Returns
    -------
    CrosstabResult
    """
    row_vals = dataset.column_values(row_variable)
    col_vals = dataset.column_values(col_variable)

    # Align — only keep pairs where both values are non-None
    pairs = [
        (r, c) for r, c in zip(row_vals, col_vals)
        if r is not None and c is not None
    ]
    if not pairs:
        raise ValueError(
            f"No valid paired observations for {row_variable!r} × {col_variable!r}"
        )

    # Build ordered category lists
    row_cats = row_order or sorted(set(p[0] for p in pairs), key=str)
    col_cats = col_order or sorted(set(p[1] for p in pairs), key=str)

    # Build observed matrix
    from collections import defaultdict
    counts: dict[tuple, int] = defaultdict(int)
    for r, c in pairs:
        counts[(r, c)] += 1

    observed = [
        [counts.get((rc, cc), 0) for cc in col_cats]
        for rc in row_cats
    ]
    row_totals = [sum(row) for row in observed]
    col_totals = [sum(observed[i][j] for i in range(len(row_cats)))
                  for j in range(len(col_cats))]
    n = sum(row_totals)

    # Chi-square test
    chi2, p_value, df, cramers_v, note = _chi_square(
        observed, row_totals, col_totals, n, len(row_cats), len(col_cats)
    )

    return CrosstabResult(
        row_variable   = row_variable,
        col_variable   = col_variable,
        row_label      = row_label or row_variable.replace("_", " ").title(),
        col_label      = col_label or col_variable.replace("_", " ").title(),
        row_categories = row_cats,
        col_categories = col_cats,
        observed       = observed,
        row_totals     = row_totals,
        col_totals     = col_totals,
        n              = n,
        chi2           = chi2,
        p_value        = p_value,
        df             = df,
        cramers_v      = cramers_v,
        significant    = p_value < 0.05,
        note           = note,
    )


# ── Internals ─────────────────────────────────────────────────

def _chi_square(
    observed:   list[list[int]],
    row_totals: list[int],
    col_totals: list[int],
    n:          int,
    n_rows:     int,
    n_cols:     int,
) -> tuple[float, float, int, float, str]:
    """
    Compute Pearson chi-square, p-value, df, and Cramer's V.
    Returns (chi2, p_value, df, cramers_v, note).
    """
    from math import isnan
    note = ""
    low_expected = 0
    chi2_stat = 0.0

    for i in range(n_rows):
        for j in range(n_cols):
            if n == 0 or row_totals[i] == 0 or col_totals[j] == 0:
                continue
            expected = row_totals[i] * col_totals[j] / n
            if expected < 5:
                low_expected += 1
            if expected > 0:
                chi2_stat += (observed[i][j] - expected) ** 2 / expected

    df   = (n_rows - 1) * (n_cols - 1)
    df   = max(df, 1)

    # p-value from chi-square distribution
    try:
        from scipy.stats import chi2 as chi2_dist
        p_value = float(1 - chi2_dist.cdf(chi2_stat, df))
    except ImportError:
        # Manual approximation if scipy not available
        p_value = _chi2_p_approx(chi2_stat, df)

    # Cramer's V
    min_dim   = min(n_rows - 1, n_cols - 1)
    cramers_v = float(np.sqrt(chi2_stat / (n * max(min_dim, 1)))) if n > 0 else 0.0
    cramers_v = min(cramers_v, 1.0)

    total_cells = n_rows * n_cols
    if low_expected > 0:
        pct = round(low_expected / total_cells * 100)
        note = (
            f"{low_expected}/{total_cells} cells ({pct}%) have expected count < 5. "
            "Chi-square result should be interpreted with caution."
        )

    return round(chi2_stat, 4), round(p_value, 6), df, round(cramers_v, 4), note


def _chi2_p_approx(chi2: float, df: int) -> float:
    """Very rough p-value approximation without scipy — used as fallback only."""
    # Based on Wilson-Hilferty normal approximation
    if df <= 0 or chi2 < 0:
        return 1.0
    z = ((chi2 / df) ** (1/3) - (1 - 2/(9*df))) / np.sqrt(2/(9*df))
    # Standard normal survival function approximation
    p = float(0.5 * (1 - float(np.tanh(z * 0.7978845608 * (1 + 0.04417 * z**2)))))
    return max(0.0, min(1.0, p))

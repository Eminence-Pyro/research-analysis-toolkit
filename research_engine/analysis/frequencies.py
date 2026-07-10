"""
research_engine/analysis/frequencies.py
Stage 9 — Analysis Engine

Frequency and percentage tables for categorical and ordinal variables.

Public API
----------
    frequency_table(dataset, variable_name)  → FrequencyTable
    all_categorical(dataset, variable_names) → list[FrequencyTable]

A FrequencyTable is a structured result object — not a DataFrame, not a
dict. It carries the variable name, rows, and metadata needed to render
itself in a report or export sheet without the caller knowing anything
about the data source.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from collections import Counter
from typing import Any

from research_engine.models import Dataset


# ── Result objects ────────────────────────────────────────────

@dataclass
class FrequencyRow:
    """One row in a frequency table."""
    value:      Any
    frequency:  int
    percent:    float
    cumulative: float = 0.0

    def __repr__(self) -> str:
        return f"{self.value!r}: n={self.frequency}, {self.percent:.1f}%"


@dataclass
class FrequencyTable:
    """
    Frequency distribution for one variable.

    Attributes
    ----------
    variable_name  : column name in the dataset
    label          : human-readable variable label (from VariableDictionary)
    rows           : list of FrequencyRow, sorted by descending frequency
    n_valid        : number of non-missing responses counted
    n_missing      : number of missing responses
    n_total        : n_valid + n_missing
    """
    variable_name: str
    label:         str
    rows:          list[FrequencyRow]
    n_valid:       int
    n_missing:     int = 0

    @property
    def n_total(self) -> int:
        return self.n_valid + self.n_missing

    def to_rows(self) -> list[tuple]:
        """
        Return plain tuples for writing to Excel or CSV.
        Columns: Value, Frequency, Percent, Cumulative %
        """
        return [
            (row.value, row.frequency, f"{row.percent:.1f}%", f"{row.cumulative:.1f}%")
            for row in self.rows
        ] + [("Total", self.n_valid, "100.0%", "")]

    def __repr__(self) -> str:
        return (
            f"FrequencyTable({self.variable_name!r}, "
            f"n={self.n_valid}, categories={len(self.rows)})"
        )


# ── Public API ────────────────────────────────────────────────

def frequency_table(
    dataset:       Dataset,
    variable_name: str,
    label:         str = "",
    sort_by:       str = "frequency",   # "frequency" | "value"
    include_missing: bool = False,
) -> FrequencyTable:
    """
    Compute a frequency table for one variable.

    Parameters
    ----------
    dataset        : the Dataset to analyse
    variable_name  : the variable to tabulate
    label          : human-readable label (defaults to variable_name)
    sort_by        : "frequency" (descending) or "value" (alphabetical/numeric)
    include_missing: if True, count None / missing responses

    Returns
    -------
    FrequencyTable
    """
    all_values = dataset.column_values(variable_name)
    missing    = sum(1 for v in all_values if v is None)
    valid      = [v for v in all_values if v is not None]

    counts = Counter(valid)
    n      = len(valid)

    if sort_by == "value":
        items = sorted(counts.items(), key=lambda x: str(x[0]))
    else:
        items = sorted(counts.items(), key=lambda x: -x[1])

    rows: list[FrequencyRow] = []
    cumulative = 0.0
    for value, freq in items:
        pct  = (freq / n * 100) if n > 0 else 0.0
        cumulative += pct
        rows.append(FrequencyRow(
            value      = value,
            frequency  = freq,
            percent    = round(pct, 1),
            cumulative = round(cumulative, 1),
        ))

    return FrequencyTable(
        variable_name = variable_name,
        label         = label or variable_name.replace("_", " ").title(),
        rows          = rows,
        n_valid       = n,
        n_missing     = missing,
    )


def all_categorical(
    dataset:        Dataset,
    variable_names: list[str],
    labels:         dict[str, str] | None = None,
    sort_by:        str = "frequency",
) -> list[FrequencyTable]:
    """
    Compute frequency tables for multiple categorical variables.

    Parameters
    ----------
    dataset        : the Dataset
    variable_names : list of variable names to tabulate
    labels         : optional {name: label} dict (e.g. from VariableDictionary)
    sort_by        : "frequency" or "value"

    Returns
    -------
    list[FrequencyTable] — one per variable, in the order given
    """
    labels = labels or {}
    return [
        frequency_table(dataset, name, label=labels.get(name, ""), sort_by=sort_by)
        for name in variable_names
    ]

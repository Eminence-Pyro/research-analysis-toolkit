"""
research_engine/analysis/
Stage 9 — Analysis Engine

Computes statistics on Dataset objects and returns structured result objects.
Nothing in this package knows about Excel, SPSS, or file formats.

Public API
----------
    from research_engine.analysis import (
        # Frequencies
        frequency_table, all_categorical,
        FrequencyTable, FrequencyRow,
        # Descriptives
        describe, describe_many, likert_summary,
        DescriptiveStats, LikertSummary, LikertItemStats,
        # Crosstabs
        crosstab,
        CrosstabResult,
    )
"""
from research_engine.analysis.frequencies import (
    frequency_table,
    all_categorical,
    FrequencyTable,
    FrequencyRow,
)
from research_engine.analysis.descriptives import (
    describe,
    describe_many,
    likert_summary,
    DescriptiveStats,
    LikertSummary,
    LikertItemStats,
)
from research_engine.analysis.crosstabs import (
    crosstab,
    CrosstabResult,
)

__all__ = [
    "frequency_table", "all_categorical", "FrequencyTable", "FrequencyRow",
    "describe", "describe_many", "likert_summary",
    "DescriptiveStats", "LikertSummary", "LikertItemStats",
    "crosstab", "CrosstabResult",
]

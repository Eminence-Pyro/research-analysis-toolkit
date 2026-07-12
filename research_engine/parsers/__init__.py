"""
research_engine/parsers/
Stage 2 — Readers (Input Layer)

Reads external formats (JSON, Word, Excel, CSV) and returns domain objects.

Public API
----------
    from research_engine.parsers import load_all, load_study, load_questionnaire
    from research_engine.parsers import StudyBundle

All parsers produce domain objects defined in research_engine.models.
They never return raw dicts, DataFrames, or file handles to callers.
"""
from research_engine.parsers.json_loader import (
    load_all,
    load_study,
    load_questionnaire,
    load_variable_dictionary,
    StudyBundle,
)

__all__ = [
    "load_all",
    "load_study",
    "load_questionnaire",
    "load_variable_dictionary",
    "StudyBundle",
]
from research_engine.parsers.schema_validator import (
    validate_config,
    validate_study_dir,
    assert_valid_study_dir,
    ConfigValidationError,
    ValidationResult,
)

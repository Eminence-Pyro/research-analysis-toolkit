"""
research_engine/validators/
Stage 8 — Validation Engine

Checks Dataset and domain objects for statistical and logical integrity.

Public API
----------
    from research_engine.validators import validate, ValidationReport
"""
from research_engine.validators.dataset_validator import validate, ValidationReport

__all__ = ["validate", "ValidationReport"]

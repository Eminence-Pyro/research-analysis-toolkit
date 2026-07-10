"""
research_engine/models/
Stage 1 — Core Domain Model

The domain layer — the language of the Research Analysis Toolkit.

All domain objects are importable directly from this package:

    from research_engine.models import (
        # Variables
        Variable, MeasurementScale, MissingValueStrategy, VariableDictionary,
        # Questionnaire
        Question, QuestionType, Section, Questionnaire,
        LIKERT_5_LABELS, LIKERT_5_AGREEMENT, LIKERT_5_FREQUENCY,
        # Study
        Facility, Study, StudyDesign, SamplingTechnique,
        # Respondent
        Response, Observation, Respondent,
        # Dataset
        Dataset,
    )

Dependency rule: This package has zero dependencies on any other
package within research_engine. All other packages depend on this one.
"""
from research_engine.models.variable import (
    Variable,
    MeasurementScale,
    MissingValueStrategy,
    VariableDictionary,
)
from research_engine.models.questionnaire import (
    Question,
    QuestionType,
    Section,
    Questionnaire,
    LIKERT_5_LABELS,
    LIKERT_5_AGREEMENT,
    LIKERT_5_FREQUENCY,
)
from research_engine.models.study import (
    Facility,
    Study,
    StudyDesign,
    SamplingTechnique,
)
from research_engine.models.respondent import (
    Response,
    Observation,
    Respondent,
)
from research_engine.models.dataset import Dataset

__all__ = [
    "Variable", "MeasurementScale", "MissingValueStrategy", "VariableDictionary",
    "Question", "QuestionType", "Section", "Questionnaire",
    "LIKERT_5_LABELS", "LIKERT_5_AGREEMENT", "LIKERT_5_FREQUENCY",
    "Facility", "Study", "StudyDesign", "SamplingTechnique",
    "Response", "Observation", "Respondent",
    "Dataset",
]

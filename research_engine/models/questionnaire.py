"""
research_engine/models/questionnaire.py
Stage 1 — Core Domain Model

Defines the structure of a research instrument:

    QuestionType   — the format of a question (Likert, categorical, open, etc.)
    Question       — a single item on the questionnaire
    Section        — a named grouping of related questions
    Questionnaire  — the complete instrument

A Questionnaire is a container for Sections, each of which holds Questions.
Questions know their own type, scale, and variable name — making it
possible to auto-build a VariableDictionary directly from a Questionnaire.

Example
-------
    >>> from research_engine.models.questionnaire import (
    ...     Question, QuestionType, Section, Questionnaire
    ... )
    >>> from research_engine.models.variable import MeasurementScale
    >>>
    >>> q1 = Question(
    ...     number="A1",
    ...     text="Staff greeted you courteously",
    ...     question_type=QuestionType.LIKERT_5,
    ...     variable_name="reception_greeting",
    ... )
    >>> sec_a = Section(key="A", title="Satisfaction with Reception")
    >>> sec_a.add(q1)
    >>> instrument = Questionnaire(title="Caregiver Satisfaction Survey")
    >>> instrument.add_section(sec_a)
    >>> instrument.question_count
    1
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ── Enumerations ─────────────────────────────────────────────

class QuestionType(str, Enum):
    """
    The format of a single question.

    LIKERT_5       — 5-point Likert scale (Very Dissatisfied → Very Satisfied).
    LIKERT_4       — 4-point scale (without neutral midpoint).
    CATEGORICAL    — Select one from a fixed list (gender, occupation, etc.).
    MULTIPLE_CHOICE — Select one or more from a list.
    ORDINAL_RANK   — Ordered categories (education level, income band).
    NUMERIC        — A numeric value (age, distance, count).
    OPEN_ENDED     — Free-text response.
    YES_NO         — Binary response (observation checklist items).
    DATE           — A date value.
    """
    LIKERT_5       = "likert_5"
    LIKERT_4       = "likert_4"
    CATEGORICAL    = "categorical"
    MULTIPLE_CHOICE = "multiple_choice"
    ORDINAL_RANK   = "ordinal_rank"
    NUMERIC        = "numeric"
    OPEN_ENDED     = "open_ended"
    YES_NO         = "yes_no"
    DATE           = "date"


# Standard Likert scale label sets — reused across instruments
LIKERT_5_LABELS: dict[int, str] = {
    1: "Very Dissatisfied",
    2: "Dissatisfied",
    3: "Neutral",
    4: "Satisfied",
    5: "Very Satisfied",
}

LIKERT_5_AGREEMENT: dict[int, str] = {
    1: "Strongly Disagree",
    2: "Disagree",
    3: "Neutral",
    4: "Agree",
    5: "Strongly Agree",
}

LIKERT_5_FREQUENCY: dict[int, str] = {
    1: "Never",
    2: "Rarely",
    3: "Sometimes",
    4: "Often",
    5: "Always",
}


# ── Question ─────────────────────────────────────────────────

@dataclass
class Question:
    """
    A single item on a research questionnaire.

    Attributes
    ----------
    number : str
        The item reference number as it appears on the instrument.
        Example: "A1", "Q3", "Section B Item 2"

    text : str
        The full wording of the question as it appears on the instrument.

    question_type : QuestionType
        The response format.

    variable_name : str
        The snake_case name of the Variable this question maps to in the
        dataset. Used to auto-build a VariableDictionary.
        Example: "reception_greeting", "gender", "age"

    section_key : str | None
        The key of the Section this question belongs to. Set automatically
        when the Question is added to a Section.

    options : list[str] | None
        For CATEGORICAL, ORDINAL_RANK, MULTIPLE_CHOICE: the fixed list of
        answer options as they appear on the questionnaire.
        For LIKERT questions: leave None (labels are in the scale dict).

    scale_labels : dict[int, str] | None
        For Likert questions: maps numeric code to label.
        Defaults to LIKERT_5_LABELS if question_type is LIKERT_5.

    valid_range : tuple[Any, Any] | None
        For NUMERIC questions: (min, max).

    required : bool
        Whether this question must have a non-missing response.
        Default True.

    notes : str
        Instrument notes (e.g., "skip to Q6 if answer is No").
    """

    number:        str
    text:          str
    question_type: QuestionType
    variable_name: str

    section_key:   str | None              = None
    options:       list[str] | None        = None
    scale_labels:  dict[int, str] | None   = None
    valid_range:   tuple[Any, Any] | None  = None
    required:      bool                    = True
    notes:         str                     = ""

    def __post_init__(self) -> None:
        # Auto-assign default Likert labels
        if self.question_type == QuestionType.LIKERT_5 and self.scale_labels is None:
            self.scale_labels = LIKERT_5_LABELS.copy()
        if self.question_type == QuestionType.LIKERT_4 and self.scale_labels is None:
            self.scale_labels = {
                1: "Dissatisfied", 2: "Somewhat Dissatisfied",
                3: "Satisfied", 4: "Very Satisfied",
            }
        if self.question_type == QuestionType.YES_NO and self.options is None:
            self.options = ["Yes", "No"]

    @property
    def is_likert(self) -> bool:
        return self.question_type in (QuestionType.LIKERT_5, QuestionType.LIKERT_4)

    @property
    def likert_range(self) -> tuple[int, int] | None:
        """Return (min, max) for Likert questions, else None."""
        if self.scale_labels:
            codes = list(self.scale_labels.keys())
            return (min(codes), max(codes))
        return None

    def __repr__(self) -> str:
        return f"Question({self.number!r}, type={self.question_type.value}, var={self.variable_name!r})"


# ── Section ──────────────────────────────────────────────────

class Section:
    """
    A named grouping of related Questions within a Questionnaire.

    Sections mirror the structure of the actual instrument (e.g.,
    "Section A: Reception", "Section B: Service Quality").

    Attributes
    ----------
    key : str
        Short identifier for this section. Used as a column prefix in
        datasets (e.g., "A" → columns SA_Q1, SA_Q2 …).
        Typically a single letter or short code.

    title : str
        Full descriptive title of the section.
        Example: "Satisfaction with Reception and Registration"

    description : str
        Optional additional context shown in reports and codebooks.
    """

    def __init__(self, key: str, title: str, description: str = "") -> None:
        if not key:
            raise ValueError("Section.key cannot be empty.")
        self.key         = key
        self.title       = title
        self.description = description
        self._questions: list[Question] = []

    def add(self, question: Question) -> None:
        """Append a Question to this Section and set its section_key."""
        question.section_key = self.key
        self._questions.append(question)

    @property
    def questions(self) -> list[Question]:
        return list(self._questions)

    @property
    def variable_names(self) -> list[str]:
        return [q.variable_name for q in self._questions]

    def __len__(self) -> int:
        return len(self._questions)

    def __iter__(self):
        return iter(self._questions)

    def __repr__(self) -> str:
        return f"Section(key={self.key!r}, title={self.title!r}, n={len(self)})"


# ── Questionnaire ─────────────────────────────────────────────

class Questionnaire:
    """
    The complete data collection instrument for a study.

    A Questionnaire is an ordered collection of Sections, each containing
    Questions. It is the bridge between the research instrument (paper or
    digital) and the domain model — a parser reads a Word document and
    produces a Questionnaire; the generator reads the Questionnaire and
    produces Responses.

    Attributes
    ----------
    title : str
        The official title of the questionnaire.

    study_title : str
        The title of the study this instrument belongs to.

    version : str
        Instrument version. Useful when questionnaires are revised.
    """

    def __init__(
        self,
        title:       str,
        study_title: str = "",
        version:     str = "1.0",
    ) -> None:
        self.title       = title
        self.study_title = study_title
        self.version     = version
        self._sections: dict[str, Section] = {}   # ordered by insertion

    def add_section(self, section: Section) -> None:
        """Add a Section. Raises ValueError if the key is already registered."""
        if section.key in self._sections:
            raise ValueError(
                f"Section {section.key!r} is already in this questionnaire."
            )
        self._sections[section.key] = section

    def get_section(self, key: str) -> Section | None:
        return self._sections.get(key)

    @property
    def sections(self) -> list[Section]:
        return list(self._sections.values())

    @property
    def section_keys(self) -> list[str]:
        return list(self._sections.keys())

    @property
    def question_count(self) -> int:
        return sum(len(s) for s in self._sections.values())

    @property
    def all_questions(self) -> list[Question]:
        """Flat list of every Question across all Sections, in order."""
        questions = []
        for section in self._sections.values():
            questions.extend(section.questions)
        return questions

    @property
    def variable_names(self) -> list[str]:
        """Ordered list of variable names for all questions."""
        return [q.variable_name for q in self.all_questions]

    def get_question_by_variable(self, variable_name: str) -> Question | None:
        """Find the Question that maps to a given variable name."""
        for q in self.all_questions:
            if q.variable_name == variable_name:
                return q
        return None

    def __repr__(self) -> str:
        return (
            f"Questionnaire(title={self.title!r}, "
            f"sections={len(self._sections)}, "
            f"questions={self.question_count})"
        )

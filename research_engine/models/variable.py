"""
research_engine/models/variable.py
Stage 1 — Core Domain Model

Defines the building blocks of a research instrument's analytical layer:

    MeasurementScale   — the level of measurement (Nominal, Ordinal, Scale)
    Variable           — a single measurable property of a respondent
    VariableDictionary — the complete catalogue of all variables in a study

The Variable is the atomic unit of analysis. Every Question on the
questionnaire maps to exactly one Variable. The VariableDictionary is the
single source of truth for variable metadata throughout the toolkit.

Example
-------
    >>> from research_engine.models.variable import (
    ...     Variable, MeasurementScale, VariableDictionary
    ... )
    >>> age = Variable(
    ...     name="age",
    ...     label="Age of respondent (years)",
    ...     scale=MeasurementScale.SCALE,
    ...     data_type=int,
    ...     valid_range=(18, 55),
    ... )
    >>> gender = Variable(
    ...     name="gender",
    ...     label="Gender of respondent",
    ...     scale=MeasurementScale.NOMINAL,
    ...     data_type=str,
    ...     allowed_values=["Male", "Female"],
    ...     spss_codes={"Male": 1, "Female": 2},
    ... )
    >>> vd = VariableDictionary()
    >>> vd.add(age)
    >>> vd.add(gender)
    >>> vd["age"].label
    'Age of respondent (years)'
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ── Enumerations ─────────────────────────────────────────────

class MeasurementScale(str, Enum):
    """
    Level of measurement for a variable.

    NOMINAL  — Categories with no inherent order (gender, occupation).
    ORDINAL  — Ordered categories with unequal intervals (Likert scale,
               education level, satisfaction category).
    SCALE    — Continuous or interval/ratio measurement (age, distance,
               section mean score).
    """
    NOMINAL = "Nominal"
    ORDINAL = "Ordinal"
    SCALE   = "Scale"


class MissingValueStrategy(str, Enum):
    """
    How missing values are handled during generation and validation.

    NONE        — No missing values allowed (default for generated data).
    SYSTEM_CODE — Missing values are coded as a numeric sentinel (e.g. 9, 99).
    EMPTY       — Missing values are empty strings or None.
    """
    NONE        = "none"
    SYSTEM_CODE = "system_code"
    EMPTY       = "empty"


# ── Variable ─────────────────────────────────────────────────

@dataclass
class Variable:
    """
    A single measurable property collected from each respondent.

    A Variable is the analytical representation of a Question. While a
    Question exists on the questionnaire (it has a number, a section, and
    wording), a Variable exists in the dataset (it has a column name, a
    scale, and a set of valid values).

    Attributes
    ----------
    name : str
        Short, snake_case identifier used as the column name in datasets
        and exports. Must be unique within a VariableDictionary.
        Example: "age", "gender", "satisfaction_section_a"

    label : str
        Human-readable description of the variable.
        Example: "Age of respondent in years"

    scale : MeasurementScale
        The level of measurement. Determines which statistics are valid.

    data_type : type
        Python type of valid values — int, float, or str.

    section : str | None
        The questionnaire section this variable belongs to, if applicable.
        Example: "A", "B", "demographics"

    question_number : str | None
        The original question number in the instrument.
        Example: "Q3", "A2", "Section B Item 4"

    allowed_values : list[Any] | None
        Exhaustive list of permitted values for NOMINAL and ORDINAL variables.
        None means any value of data_type is permitted (used for SCALE).
        Example: ["Male", "Female"]  or  [1, 2, 3, 4, 5]

    valid_range : tuple[Any, Any] | None
        (min, max) inclusive range for SCALE variables.
        Example: (18, 55) for age, (1, 5) for a Likert item

    spss_codes : dict[str, int] | None
        Mapping from string label to numeric code for SPSS export.
        Example: {"Male": 1, "Female": 2, "Unknown": 9}
        None for variables that are already numeric.

    missing_code : int | None
        Numeric code used to represent missing/unknown values in SPSS export.
        Conventional values: 9, 99, 999 depending on scale.

    missing_strategy : MissingValueStrategy
        How missing values are handled. Default: NONE (no missings in
        synthetic data).

    is_derived : bool
        True if this variable is computed from other variables rather than
        collected directly (e.g., section mean score, satisfaction category).

    notes : str
        Free-text notes for the codebook.
    """

    name:              str
    label:             str
    scale:             MeasurementScale
    data_type:         type

    section:           str | None             = None
    question_number:   str | None             = None
    allowed_values:    list[Any] | None       = None
    valid_range:       tuple[Any, Any] | None = None
    spss_codes:        dict[str, int] | None  = None
    missing_code:      int | None             = None
    missing_strategy:  MissingValueStrategy   = MissingValueStrategy.NONE
    is_derived:        bool                   = False
    notes:             str                    = ""

    # ── Validation on creation ────────────────────────────────

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Variable.name cannot be empty.")
        if not self.name.replace("_", "").isalnum():
            raise ValueError(
                f"Variable.name must be alphanumeric with underscores. Got: {self.name!r}"
            )
        if self.scale in (MeasurementScale.NOMINAL, MeasurementScale.ORDINAL):
            if self.allowed_values is None and self.valid_range is None:
                raise ValueError(
                    f"Variable {self.name!r} is {self.scale.value} — "
                    "must specify either allowed_values or valid_range."
                )
        if self.valid_range is not None:
            lo, hi = self.valid_range
            if lo > hi:
                raise ValueError(
                    f"Variable {self.name!r}: valid_range min ({lo}) > max ({hi})."
                )

    # ── Convenience methods ───────────────────────────────────

    def validate_value(self, value: Any) -> bool:
        """
        Return True if *value* is a valid observation for this variable.

        Checks:
        - Value is of the correct data_type (or None if missings allowed)
        - For NOMINAL/ORDINAL with allowed_values: value is in allowed_values
        - For SCALE with valid_range: value is within [min, max]
        """
        if value is None:
            return self.missing_strategy != MissingValueStrategy.NONE

        if not isinstance(value, self.data_type):
            try:
                self.data_type(value)
            except (ValueError, TypeError):
                return False

        if self.allowed_values is not None:
            return value in self.allowed_values

        if self.valid_range is not None:
            lo, hi = self.valid_range
            return lo <= value <= hi

        return True

    def to_spss_code(self, value: Any) -> int:
        """
        Return the SPSS numeric code for a labelled value.
        Returns missing_code (or 9) if value not found in spss_codes.
        """
        if self.spss_codes is None:
            if isinstance(value, (int, float)):
                return int(value)
            return self.missing_code or 9
        return self.spss_codes.get(str(value), self.missing_code or 9)

    def __repr__(self) -> str:
        return (
            f"Variable(name={self.name!r}, scale={self.scale.value}, "
            f"type={self.data_type.__name__})"
        )


# ── VariableDictionary ───────────────────────────────────────

class VariableDictionary:
    """
    The complete catalogue of all variables in a study.

    Acts as the single source of truth for variable metadata throughout
    the toolkit. Every module that needs to know the name, scale, allowed
    values, or SPSS codes for a variable asks the VariableDictionary.

    Variables are stored in insertion order. Names must be unique.

    Example
    -------
        >>> vd = VariableDictionary(study_name="Immunization Satisfaction Study")
        >>> vd.add(Variable("age", "Age (years)", MeasurementScale.SCALE, int,
        ...                 valid_range=(18, 55)))
        >>> vd.add(Variable("gender", "Gender", MeasurementScale.NOMINAL, str,
        ...                 allowed_values=["Male", "Female"],
        ...                 spss_codes={"Male": 1, "Female": 2}))
        >>> len(vd)
        2
        >>> vd["age"].scale
        <MeasurementScale.SCALE: 'Scale'>
        >>> [v.name for v in vd.by_section("demographics")]
        ['age', 'gender', ...]
    """

    def __init__(self, study_name: str = "") -> None:
        self.study_name = study_name
        self._variables: dict[str, Variable] = {}

    def add(self, variable: Variable) -> None:
        """Add a Variable. Raises ValueError if name already registered."""
        if variable.name in self._variables:
            raise ValueError(
                f"Variable {variable.name!r} is already in the dictionary."
            )
        self._variables[variable.name] = variable

    def get(self, name: str) -> Variable | None:
        """Return Variable by name, or None if not found."""
        return self._variables.get(name)

    def by_section(self, section: str) -> list[Variable]:
        """Return all variables belonging to a given section."""
        return [v for v in self._variables.values() if v.section == section]

    def by_scale(self, scale: MeasurementScale) -> list[Variable]:
        """Return all variables with a given measurement scale."""
        return [v for v in self._variables.values() if v.scale == scale]

    @property
    def names(self) -> list[str]:
        """Ordered list of all variable names."""
        return list(self._variables.keys())

    @property
    def sections(self) -> list[str]:
        """Sorted unique list of section names (excluding None)."""
        return sorted({v.section for v in self._variables.values() if v.section})

    def to_codebook_rows(self) -> list[tuple]:
        """
        Return a list of tuples suitable for writing to a codebook sheet.
        Columns: Name, Label, Type, Scale, Section, Values/Range, SPSS Codes, Notes
        """
        rows = []
        for v in self._variables.values():
            if v.allowed_values:
                values_str = " / ".join(str(x) for x in v.allowed_values[:8])
                if len(v.allowed_values) > 8:
                    values_str += "…"
            elif v.valid_range:
                values_str = f"{v.valid_range[0]} – {v.valid_range[1]}"
            else:
                values_str = "—"

            spss_str = (
                ", ".join(f"{k}={v2}" for k, v2 in list((v.spss_codes or {}).items())[:5])
                or "—"
            )
            rows.append((
                v.name,
                v.label,
                v.data_type.__name__,
                v.scale.value,
                v.section or "—",
                v.question_number or "—",
                values_str,
                spss_str,
                v.notes,
            ))
        return rows

    def __getitem__(self, name: str) -> Variable:
        try:
            return self._variables[name]
        except KeyError:
            raise KeyError(f"Variable {name!r} not found in VariableDictionary.")

    def __contains__(self, name: str) -> bool:
        return name in self._variables

    def __len__(self) -> int:
        return len(self._variables)

    def __iter__(self):
        return iter(self._variables.values())

    def __repr__(self) -> str:
        return (
            f"VariableDictionary(study={self.study_name!r}, "
            f"n_variables={len(self)})"
        )

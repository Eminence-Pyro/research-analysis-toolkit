"""
research_engine/models/respondent.py
Stage 1 — Core Domain Model

Defines a study participant and their responses:

    Response     — a single answer to a single Question
    Observation  — a Yes/No facility observation record
    Respondent   — a study participant with demographics and all responses

A Respondent is the unit of analysis. Every row in the final dataset
represents one Respondent. The Respondent holds all of their demographic
attributes and every Response they gave to the questionnaire.

Design note: Demographics are stored as a plain dict rather than fixed
fields because different studies collect entirely different demographic
variables. The VariableDictionary defines which demographics exist;
the dict stores their values.

Example
-------
    >>> from research_engine.models.respondent import Respondent, Response
    >>>
    >>> r = Respondent(
    ...     respondent_id="R001",
    ...     facility_id=1,
    ...     demographics={
    ...         "age": 28,
    ...         "gender": "Female",
    ...         "education": "Secondary",
    ...     }
    ... )
    >>> r.add_response(Response(variable_name="reception_greeting", value=4))
    >>> r.add_response(Response(variable_name="reception_speed",    value=3))
    >>> r.get_response("reception_greeting").value
    4
    >>> r.likert_mean(variable_names=["reception_greeting","reception_speed"])
    3.5
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Response ─────────────────────────────────────────────────

@dataclass
class Response:
    """
    A single answer given by a Respondent to a single Question.

    Attributes
    ----------
    variable_name : str
        The variable name of the Question this response answers.
        Must match a Variable in the study's VariableDictionary.

    value : Any
        The raw response value.
        - Likert: int (1–5)
        - Categorical: str ("Female", "Married", etc.)
        - Numeric: int or float (28, 3.5)
        - Yes/No: str ("Yes" or "No")

    is_missing : bool
        True if this response was not collected or is unknown.
        Generated datasets should have is_missing=False for all responses.
    """
    variable_name: str
    value:         Any
    is_missing:    bool = False

    def __repr__(self) -> str:
        return f"Response({self.variable_name!r}={self.value!r})"


# ── Observation ───────────────────────────────────────────────

@dataclass
class Observation:
    """
    A single facility observation record linked to a respondent visit.

    Observation data is collected by a researcher watching the facility
    during a respondent's visit — not reported by the respondent themselves.
    It captures physical and procedural aspects of the facility.

    Attributes
    ----------
    variable_name : str
        The key for this observation item.
        Example: "cleanliness", "vaccine_availability", "waiting_time_ok"

    value : str
        "Yes" or "No" for checklist items.
        May also be a rating or free text for extended observation forms.

    facility_id : int
        The facility at which this observation was made.
    """
    variable_name: str
    value:         str
    facility_id:   int = 0


# ── Respondent ────────────────────────────────────────────────

class Respondent:
    """
    A single study participant — the unit of analysis.

    A Respondent holds:
    - A unique identifier
    - A facility assignment
    - A dict of demographic values
    - An ordered list of Responses to questionnaire items
    - An optional list of Observation records

    Attributes
    ----------
    respondent_id : str
        Unique identifier. Format is study-specific.
        Example: "R001", "IMM-042"

    facility_id : int
        The ID of the Facility where this respondent was recruited.

    demographics : dict[str, Any]
        All demographic variable values for this respondent.
        Keys are variable names (must exist in the study's VariableDictionary).
        Example: {"age": 28, "gender": "Female", "education": "Secondary"}

    responses : list[Response]
        All questionnaire responses, in question order.

    observations : list[Observation]
        Facility observation records linked to this respondent's visit.
    """

    def __init__(
        self,
        respondent_id: str,
        facility_id:   int              = 0,
        demographics:  dict[str, Any]  | None = None,
    ) -> None:
        if not respondent_id:
            raise ValueError("Respondent.respondent_id cannot be empty.")
        self.respondent_id = respondent_id
        self.facility_id   = facility_id
        self.demographics: dict[str, Any]  = demographics or {}
        self._responses:   dict[str, Response]   = {}
        self._observations: list[Observation]    = []

    # ── Response management ───────────────────────────────────

    def add_response(self, response: Response) -> None:
        """
        Add or overwrite a Response for the given variable.
        If a response for this variable already exists, it is replaced.
        """
        self._responses[response.variable_name] = response

    def get_response(self, variable_name: str) -> Response | None:
        """Return the Response for a given variable, or None."""
        return self._responses.get(variable_name)

    def get_value(self, variable_name: str, default: Any = None) -> Any:
        """
        Return the raw value of a response or demographic variable.
        Checks responses first, then demographics. Returns default if not found.
        """
        if variable_name in self._responses:
            r = self._responses[variable_name]
            return None if r.is_missing else r.value
        return self.demographics.get(variable_name, default)

    @property
    def responses(self) -> list[Response]:
        return list(self._responses.values())

    @property
    def response_dict(self) -> dict[str, Any]:
        """Dict of variable_name → value for all non-missing responses."""
        return {
            name: r.value
            for name, r in self._responses.items()
            if not r.is_missing
        }

    # ── Observation management ────────────────────────────────

    def add_observation(self, obs: Observation) -> None:
        self._observations.append(obs)

    @property
    def observations(self) -> list[Observation]:
        return list(self._observations)

    @property
    def observation_dict(self) -> dict[str, str]:
        """Dict of variable_name → value for all observations."""
        return {o.variable_name: o.value for o in self._observations}

    # ── Computed statistics ───────────────────────────────────

    def likert_mean(self, variable_names: list[str]) -> float | None:
        """
        Return the mean of Likert response values for the given variable names.
        Returns None if no valid numeric responses found.
        """
        values = []
        for name in variable_names:
            r = self._responses.get(name)
            if r and not r.is_missing and isinstance(r.value, (int, float)):
                values.append(float(r.value))
        if not values:
            return None
        return round(sum(values) / len(values), 4)

    def section_mean(self, section_variable_names: list[str]) -> float | None:
        """Alias for likert_mean — explicitly named for section-level means."""
        return self.likert_mean(section_variable_names)

    def to_flat_dict(self) -> dict[str, Any]:
        """
        Return a single flat dict of all data for this respondent:
        demographics + responses + observations.
        Used by exporters to produce dataset rows.
        """
        row: dict[str, Any] = {"respondent_id": self.respondent_id,
                                "facility_id":   self.facility_id}
        row.update(self.demographics)
        row.update(self.response_dict)
        row.update(self.observation_dict)
        return row

    def __repr__(self) -> str:
        return (
            f"Respondent(id={self.respondent_id!r}, "
            f"facility={self.facility_id}, "
            f"responses={len(self._responses)})"
        )

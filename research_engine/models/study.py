"""
research_engine/models/study.py
Stage 1 — Core Domain Model

Defines the top-level research project objects:

    StudyDesign    — the epidemiological design of the study
    Facility       — a single study site (PHC, hospital, school, clinic)
    Study          — the complete research project

A Study is the root object of the entire application. It holds the
Questionnaire, the list of Facilities, and the study's metadata.
Every generated Dataset belongs to exactly one Study.

Example
-------
    >>> from research_engine.models.study import Study, Facility, StudyDesign
    >>> from research_engine.models.questionnaire import Questionnaire
    >>>
    >>> phc_1 = Facility(id=1, name="Ward I PHC", ward="I", lga="Aba North")
    >>> phc_2 = Facility(id=2, name="Ward II PHC", ward="II", lga="Aba North")
    >>>
    >>> study = Study(
    ...     title="Caregiver Satisfaction with Immunization Services",
    ...     design=StudyDesign.CROSS_SECTIONAL,
    ...     setting="Urban PHCs, Wards I–IV, Aba North LGA, Abia State",
    ...     target_n=120,
    ... )
    >>> study.add_facility(phc_1)
    >>> study.add_facility(phc_2)
    >>> study.n_facilities
    2
    >>> study.respondents_per_facility
    60
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from research_engine.models.questionnaire import Questionnaire


# ── Enumerations ─────────────────────────────────────────────

class StudyDesign(str, Enum):
    """
    The epidemiological or research design of the study.

    CROSS_SECTIONAL  — Data collected at one point in time (most common).
    COHORT           — Participants followed forward over time.
    CASE_CONTROL     — Cases with outcome compared to controls without.
    DESCRIPTIVE      — Describes characteristics without causal inference.
    EXPERIMENTAL     — Controlled intervention (RCT).
    QUALITATIVE      — Non-numeric, thematic analysis.
    MIXED_METHODS    — Combination of quantitative and qualitative.
    """
    CROSS_SECTIONAL = "Cross-sectional"
    COHORT          = "Cohort"
    CASE_CONTROL    = "Case-control"
    DESCRIPTIVE     = "Descriptive"
    EXPERIMENTAL    = "Experimental / RCT"
    QUALITATIVE     = "Qualitative"
    MIXED_METHODS   = "Mixed methods"


class SamplingTechnique(str, Enum):
    """
    The method used to select study participants.

    SYSTEMATIC           — Every nth person from a list.
    SIMPLE_RANDOM        — Random selection from full population.
    STRATIFIED_RANDOM    — Random within defined strata.
    PURPOSIVE            — Deliberate selection for specific characteristics.
    CONVENIENCE          — Whoever is available (common in clinic studies).
    CONSECUTIVE          — Every eligible person during the study period.
    """
    SYSTEMATIC        = "Systematic random sampling"
    SIMPLE_RANDOM     = "Simple random sampling"
    STRATIFIED_RANDOM = "Stratified random sampling"
    PURPOSIVE         = "Purposive sampling"
    CONVENIENCE       = "Convenience sampling"
    CONSECUTIVE       = "Consecutive sampling"


# ── Facility ─────────────────────────────────────────────────

@dataclass
class Facility:
    """
    A single study site where data is collected.

    Facilities are the spatial unit of a multi-site study. Each Facility
    receives a fixed allocation of respondents. Facility-level fixed effects
    can be applied during data generation to simulate between-facility
    variation in service quality.

    Attributes
    ----------
    id : int
        Unique numeric identifier. Used as a foreign key in respondent records.

    name : str
        Full name of the facility.
        Example: "Ward I Primary Health Centre"

    ward : str
        Ward name or number.

    lga : str
        Local Government Area.

    state : str
        State.

    facility_type : str
        Type of facility (PHC, General Hospital, Specialist Hospital, School, etc.)

    n_respondents : int
        Number of respondents to be collected at this facility.
        Set automatically by Study when target_n and facilities are configured.

    satisfaction_effect : float
        A small additive effect applied to base satisfaction scores during
        generation to simulate between-facility quality differences.
        Example: +0.3 (better-performing facility), -0.1 (weaker facility).
        Range: typically -0.5 to +0.5.

    notes : str
        Any additional notes about this facility.
    """

    id:                 int
    name:               str
    ward:               str               = ""
    lga:                str               = ""
    state:              str               = ""
    facility_type:      str               = "Primary Health Centre"
    n_respondents:      int               = 0
    satisfaction_effect: float            = 0.0
    notes:              str               = ""

    def __repr__(self) -> str:
        return f"Facility(id={self.id}, name={self.name!r}, n={self.n_respondents})"


# ── Study ─────────────────────────────────────────────────────

class Study:
    """
    The complete research project — the root object of the application.

    A Study owns:
    - Its Questionnaire (the data collection instrument)
    - Its list of Facilities (study sites)
    - Its metadata (title, design, setting, population, target sample size)

    Every Dataset, Respondent, and Observation belongs to exactly one Study.

    Attributes
    ----------
    title : str
        Full title of the study.

    design : StudyDesign
        The research design.

    setting : str
        A plain-language description of the study setting.
        Example: "Urban PHCs, Wards I–IV, Aba North LGA, Abia State"

    population : str
        A description of the target population.
        Example: "Caregivers of children 0–23 months attending immunization clinics"

    target_n : int
        The total planned sample size.

    sampling_technique : SamplingTechnique
        The sampling method.

    questionnaire : Questionnaire | None
        The data collection instrument. Assigned after construction via
        ``study.questionnaire = instrument``.
    """

    def __init__(
        self,
        title:              str,
        design:             StudyDesign          = StudyDesign.CROSS_SECTIONAL,
        setting:            str                  = "",
        population:         str                  = "",
        target_n:           int                  = 0,
        sampling_technique: SamplingTechnique    = SamplingTechnique.CONSECUTIVE,
    ) -> None:
        self.title              = title
        self.design             = design
        self.setting            = setting
        self.population         = population
        self.target_n           = target_n
        self.sampling_technique = sampling_technique
        self.questionnaire: Questionnaire | None = None
        self._facilities: list[Facility] = []

    # ── Facilities ────────────────────────────────────────────

    def add_facility(self, facility: Facility) -> None:
        """Add a Facility. IDs must be unique within a Study."""
        existing_ids = {f.id for f in self._facilities}
        if facility.id in existing_ids:
            raise ValueError(
                f"Facility with id={facility.id} already exists in this study."
            )
        self._facilities.append(facility)
        self._distribute_respondents()

    @property
    def facilities(self) -> list[Facility]:
        return list(self._facilities)

    @property
    def n_facilities(self) -> int:
        return len(self._facilities)

    @property
    def respondents_per_facility(self) -> int:
        """
        Equal allocation of respondents across facilities.
        Returns 0 if no facilities or target_n not set.
        """
        if not self._facilities or not self.target_n:
            return 0
        return self.target_n // self.n_facilities

    def facility_assignments(self) -> list[int]:
        """
        Return a flat list of facility IDs, one per planned respondent,
        in facility order. Used by generators to assign respondents.

        Example: 2 facilities × 3 respondents each → [1, 1, 1, 2, 2, 2]
        """
        assignments = []
        for facility in self._facilities:
            assignments.extend([facility.id] * facility.n_respondents)
        return assignments

    def _distribute_respondents(self) -> None:
        """Distribute target_n equally across current facilities."""
        if not self._facilities or not self.target_n:
            return
        per_facility = self.target_n // self.n_facilities
        remainder    = self.target_n % self.n_facilities
        for i, facility in enumerate(self._facilities):
            # Give the remainder to the last facility
            facility.n_respondents = per_facility + (1 if i == self.n_facilities - 1 else 0) * remainder

    # ── Questionnaire assignment ───────────────────────────────

    @property
    def questionnaire(self) -> Questionnaire | None:
        return self._questionnaire

    @questionnaire.setter
    def questionnaire(self, instrument: Questionnaire | None) -> None:
        self._questionnaire = instrument

    # ── Convenience ───────────────────────────────────────────

    @property
    def is_ready(self) -> bool:
        """
        True if the Study has enough configuration to run the generator:
        - A questionnaire is assigned
        - At least one facility
        - A positive target_n
        """
        return (
            self._questionnaire is not None
            and len(self._facilities) > 0
            and self.target_n > 0
        )

    def summary(self) -> str:
        """Return a multi-line human-readable summary of the study."""
        lines = [
            f"Study    : {self.title}",
            f"Design   : {self.design.value}",
            f"Setting  : {self.setting}",
            f"Population: {self.population}",
            f"Sample N : {self.target_n}",
            f"Sampling : {self.sampling_technique.value}",
            f"Facilities: {self.n_facilities}",
        ]
        for fac in self._facilities:
            lines.append(f"  [{fac.id}] {fac.name}  (n={fac.n_respondents})")
        if self._questionnaire:
            lines.append(
                f"Instrument: {self._questionnaire.title} "
                f"({self._questionnaire.question_count} questions)"
            )
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"Study(title={self.title!r}, n={self.target_n}, "
            f"facilities={self.n_facilities})"
        )

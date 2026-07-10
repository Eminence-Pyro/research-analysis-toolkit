"""
research_engine/validators/dataset_validator.py
Stage 8 — Validation Engine

Checks a Dataset for statistical consistency and logical integrity
before export.

All checks produce structured, machine-readable results. The caller
decides how to display them (rich terminal, Excel sheet, text file).

Public API
----------
    validate(dataset, study, expected_n)  → ValidationReport

Example
-------
    >>> from research_engine.validators.dataset_validator import validate
    >>> report = validate(dataset, study)
    >>> report.is_ready
    True
    >>> report.summary()
    '13 passed, 0 warnings, 0 errors'
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import numpy as np
from collections import Counter

from research_engine.models import Dataset, Study


# ── ValidationReport ─────────────────────────────────────────

@dataclass
class ValidationCheck:
    """One individual validation check result."""
    status:  str    # "pass", "warn", "error"
    message: str
    detail:  Any = None


@dataclass
class ValidationReport:
    """
    The complete output of the validation engine.

    Attributes
    ----------
    checks     : list of individual check results
    dataset_n  : number of respondents validated
    study_title: title of the study
    """
    checks:      list[ValidationCheck] = field(default_factory=list)
    dataset_n:   int  = 0
    study_title: str  = ""

    def _by_status(self, status: str) -> list[ValidationCheck]:
        return [c for c in self.checks if c.status == status]

    @property
    def passed(self)   -> list[ValidationCheck]: return self._by_status("pass")
    @property
    def warnings(self) -> list[ValidationCheck]: return self._by_status("warn")
    @property
    def errors(self)   -> list[ValidationCheck]: return self._by_status("error")

    @property
    def is_ready(self) -> bool:
        return len(self.errors) == 0

    def summary(self) -> str:
        return (
            f"{len(self.passed)} passed, "
            f"{len(self.warnings)} warnings, "
            f"{len(self.errors)} errors"
        )

    def to_rows(self) -> list[tuple[str, str]]:
        """Return (status_label, message) tuples for export."""
        label = {"pass": "✓ PASS", "warn": "⚠ WARN", "error": "✗ ERR"}
        return [(label[c.status], c.message) for c in self.checks]


# ── Public validator ──────────────────────────────────────────

def validate(
    dataset:     Dataset,
    study:       Study  | None = None,
    expected_n:  int    | None = None,
) -> ValidationReport:
    """
    Run all validation checks on a Dataset.

    Parameters
    ----------
    dataset    : the generated Dataset
    study      : optional Study — used to check facility assignments and N
    expected_n : override expected sample size (defaults to study.target_n or 100)

    Returns
    -------
    ValidationReport
    """
    report = ValidationReport(dataset_n=len(dataset), study_title=dataset.study_title)
    min_n  = expected_n or (study.target_n if study else 100)

    _check_sample_size(report, dataset, min_n)
    _check_unique_ids(report, dataset)
    _check_likert_range(report, dataset)
    _check_education_satisfaction(report, dataset)
    _check_distance_satisfaction(report, dataset)
    _check_observation_consistency(report, dataset)
    _check_missing_values(report, dataset)
    _check_satisfaction_distribution(report, dataset)
    _check_section_means(report, dataset)
    if study:
        _check_facility_assignments(report, dataset, study)

    return report


# ── Individual checks ─────────────────────────────────────────

def _check_sample_size(r: ValidationReport, ds: Dataset, min_n: int) -> None:
    n = len(ds)
    if n >= min_n:
        r.checks.append(ValidationCheck("pass", f"Sample size: {n} respondents (≥{min_n} ✓)"))
    else:
        r.checks.append(ValidationCheck("error", f"Sample size {n} is below expected {min_n}"))


def _check_unique_ids(r: ValidationReport, ds: Dataset) -> None:
    ids = [resp.respondent_id for resp in ds]
    if len(set(ids)) == len(ids):
        r.checks.append(ValidationCheck("pass", "All respondent IDs are unique"))
    else:
        dups = len(ids) - len(set(ids))
        r.checks.append(ValidationCheck("error", f"{dups} duplicate respondent IDs found"))


def _check_likert_range(r: ValidationReport, ds: Dataset) -> None:
    bad: list[tuple] = []
    for resp in ds:
        for response in resp.responses:
            if response.variable_name.startswith("s") and "q" in response.variable_name:
                val = response.value
                if not isinstance(val, int) or not (1 <= val <= 5):
                    bad.append((resp.respondent_id, response.variable_name, val))
    # Discover how many Likert items there are
    if ds.n > 0:
        first  = next(iter(ds))
        n_likert = sum(
            1 for r2 in first.responses
            if r2.variable_name.startswith("s") and "q" in r2.variable_name
        )
    else:
        n_likert = 0
    if not bad:
        r.checks.append(ValidationCheck("pass", f"All {n_likert} Likert items within valid 1–5 range"))
    else:
        r.checks.append(ValidationCheck("error",
            f"{len(bad)} out-of-range Likert values", detail=bad[:5]))


def _check_education_satisfaction(r: ValidationReport, ds: Dataset) -> None:
    edu_ranks = ds.column_values("education_rank")
    sat_means  = ds.column_values("overall_mean")
    if len(edu_ranks) == len(sat_means) and len(edu_ranks) > 1:
        corr = float(np.corrcoef(edu_ranks, sat_means)[0, 1])
        if corr > 0:
            r.checks.append(ValidationCheck("pass",
                f"Education–satisfaction correlation: r={corr:.3f} (positive ✓)"))
        else:
            r.checks.append(ValidationCheck("warn",
                f"Education–satisfaction correlation negative: r={corr:.3f}"))
    else:
        r.checks.append(ValidationCheck("warn",
            "Could not compute education–satisfaction correlation (missing ranks)"))


def _check_distance_satisfaction(r: ValidationReport, ds: Dataset) -> None:
    distances = ds.column_values("distance_to_facility_km")
    sat_means  = ds.column_values("overall_mean")
    if len(distances) == len(sat_means) and len(distances) > 1:
        corr = float(np.corrcoef(distances, sat_means)[0, 1])
        if corr < 0:
            r.checks.append(ValidationCheck("pass",
                f"Distance–satisfaction correlation: r={corr:.3f} (negative ✓)"))
        else:
            r.checks.append(ValidationCheck("warn",
                f"Distance–satisfaction correlation positive: r={corr:.3f}"))
    else:
        r.checks.append(ValidationCheck("warn",
            "Could not compute distance–satisfaction correlation"))


def _check_observation_consistency(r: ValidationReport, ds: Dataset) -> None:
    env_means   = [float(v) for v in ds.column_values("mean_D") if v is not None]
    obs_counts  = []
    for resp in ds:
        oc = resp.get_value("obs_yes_count")
        if oc is not None:
            try: obs_counts.append(int(oc))
            except (ValueError, TypeError): pass
    if env_means and obs_counts and len(env_means) == len(obs_counts):
        corr = float(np.corrcoef(env_means, obs_counts)[0, 1])
        if corr > 0:
            r.checks.append(ValidationCheck("pass",
                f"Environment score–observation consistency: r={corr:.3f} (positive ✓)"))
        else:
            r.checks.append(ValidationCheck("warn",
                f"Observation data inconsistent with environment scores: r={corr:.3f}"))
    else:
        r.checks.append(ValidationCheck("warn", "Observation data not available for consistency check"))


def _check_missing_values(r: ValidationReport, ds: Dataset) -> None:
    missing = sum(
        1 for resp in ds
        for response in resp.responses
        if response.is_missing
    )
    if missing == 0:
        r.checks.append(ValidationCheck("pass", "No missing values in dataset"))
    else:
        r.checks.append(ValidationCheck("warn", f"{missing} missing values detected"))


def _check_satisfaction_distribution(r: ValidationReport, ds: Dataset) -> None:
    cats = Counter(ds.column_values("satisfaction_category"))
    r.checks.append(ValidationCheck("pass",
        f"Satisfaction distribution: {dict(cats)}"))


def _check_section_means(r: ValidationReport, ds: Dataset) -> None:
    section_keys = [
        k.split("_")[1] for k in ds.variable_names
        if k.startswith("mean_") and len(k.split("_")) == 2
    ]
    for sec in sorted(set(section_keys)):
        vals = [float(v) for v in ds.column_values(f"mean_{sec}") if v is not None]
        if vals:
            r.checks.append(ValidationCheck("pass",
                f"Section {sec}: mean={np.mean(vals):.2f}, SD={np.std(vals):.2f}"))


def _check_facility_assignments(r: ValidationReport, ds: Dataset, study: Study) -> None:
    expected_ids = {f.id for f in study.facilities}
    actual_ids   = set(ds.facility_ids)
    if actual_ids == expected_ids:
        r.checks.append(ValidationCheck("pass",
            f"All {len(expected_ids)} facilities represented in dataset"))
    else:
        missing = expected_ids - actual_ids
        extra   = actual_ids - expected_ids
        msg = []
        if missing: msg.append(f"missing facilities: {missing}")
        if extra:   msg.append(f"unexpected facilities: {extra}")
        r.checks.append(ValidationCheck("warn", f"Facility assignment issues — {'; '.join(msg)}"))

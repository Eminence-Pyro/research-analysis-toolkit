"""
research_engine/parsers/json_loader.py
Stage 2 — Readers (Input Layer)

Loads study configuration from JSON files and returns fully
constructed domain model objects.

This is the bridge between the study config files in studies/<name>/
and the research_engine domain model. After this module, no downstream
code needs to know that JSON files exist — everything is domain objects.

Public API
----------
    load_study(config_path)          → Study
    load_questionnaire(q_path)       → Questionnaire
    load_variable_dictionary(q_path, demo_path) → VariableDictionary
    load_all(study_dir)              → StudyBundle

Example
-------
    >>> from pathlib import Path
    >>> from research_engine.parsers.json_loader import load_all
    >>> bundle = load_all(Path("studies/immunization_aba"))
    >>> bundle.study.title
    'Pattern of Caregiver Satisfaction with Immunization Services'
    >>> bundle.questionnaire.question_count
    25
    >>> len(bundle.variable_dictionary)
    37
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from research_engine.models import (
    Variable, MeasurementScale, MissingValueStrategy, VariableDictionary,
    Question, QuestionType, Section, Questionnaire,
    Facility, Study, StudyDesign, SamplingTechnique,
)


# ── StudyBundle ───────────────────────────────────────────────

@dataclass
class StudyBundle:
    """
    Everything the generation and analysis pipeline needs for one study.

    Produced by load_all() and passed directly to generators, validators,
    exporters, and report builders.

    Attributes
    ----------
    study               : the Study with Facilities configured
    questionnaire       : the full instrument
    variable_dictionary : metadata for every variable
    raw_demographics    : the raw demographics config dict (for generators)
    raw_observation     : the raw observation checklist config dict
    """
    study:               Study
    questionnaire:       Questionnaire
    variable_dictionary: VariableDictionary
    raw_demographics:    dict
    raw_observation:     dict


# ── Public loaders ────────────────────────────────────────────

def load_study(config_path: str | Path) -> Study:
    """
    Load a Study object from a study config.json (or config.py values dict).

    The config JSON must contain:
        {
          "title":              "...",
          "setting":            "...",
          "population":         "...",
          "target_n":           120,
          "design":             "Cross-sectional",       // optional
          "sampling_technique": "Consecutive sampling",  // optional
          "facilities": [
            {"id": 1, "name": "Ward I PHC", "ward": "I",
             "satisfaction_effect": 0.3},
            ...
          ]
        }
    """
    cfg = _load_json(config_path)
    return _build_study(cfg)


def load_questionnaire(questionnaire_path: str | Path) -> Questionnaire:
    """
    Load a Questionnaire object from a questionnaire.json file.

    The JSON must contain:
        {
          "title": "...",
          "scale": {"1": "Very Dissatisfied", ..., "5": "Very Satisfied"},
          "sections": {
            "A": {
              "title": "...",
              "items": ["Question text 1", "Question text 2", ...]
            },
            ...
          }
        }
    """
    cfg = _load_json(questionnaire_path)
    return _build_questionnaire(cfg)


def load_variable_dictionary(
    questionnaire_path: str | Path,
    demographics_path:  str | Path | None = None,
) -> VariableDictionary:
    """
    Build a VariableDictionary from questionnaire and (optionally)
    demographics config files.

    The questionnaire produces Likert variables for each item and a
    section-mean variable per section.
    The demographics config produces one Variable per demographic field.
    """
    q_cfg = _load_json(questionnaire_path)
    vd    = VariableDictionary()
    _add_questionnaire_variables(vd, q_cfg)
    if demographics_path:
        d_cfg = _load_json(demographics_path)
        _add_demographic_variables(vd, d_cfg)
    return vd


def load_all(study_dir: str | Path,
             validate: bool = True) -> StudyBundle:
    """
    Load everything for a study from its directory.

    Expects the directory to contain:
        config.json          — study metadata and facilities
        questionnaire.json   — instrument sections and items
        demographics.json    — demographic distributions
        observation.json     — observation checklist items

    Returns a StudyBundle with Study, Questionnaire, and VariableDictionary
    all constructed and cross-linked.
    """
    d = Path(study_dir)
    _assert_file(d / "config.json")
    _assert_file(d / "questionnaire.json")
    _assert_file(d / "demographics.json")

    cfg   = _load_json(d / "config.json")
    q_cfg = _load_json(d / "questionnaire.json")
    dm_cfg = _load_json(d / "demographics.json")
    ob_cfg = _load_json(d / "observation.json") if (d / "observation.json").exists() else {}

    study = _build_study(cfg)
    questionnaire = _build_questionnaire(q_cfg)
    study.questionnaire = questionnaire

    vd = VariableDictionary(study_name=study.title)
    _add_questionnaire_variables(vd, q_cfg)
    _add_demographic_variables(vd, dm_cfg)
    _add_observation_variables(vd, ob_cfg)

    return StudyBundle(
        study               = study,
        questionnaire       = questionnaire,
        variable_dictionary = vd,
        raw_demographics    = dm_cfg,
        raw_observation     = ob_cfg,
    )


# ── Internal builders ─────────────────────────────────────────

def _build_study(cfg: dict) -> Study:
    design_map = {d.value: d for d in StudyDesign}
    sampling_map = {s.value: s for s in SamplingTechnique}

    study = Study(
        title              = cfg["title"],
        design             = design_map.get(cfg.get("design",""), StudyDesign.CROSS_SECTIONAL),
        setting            = cfg.get("setting", ""),
        population         = cfg.get("population", ""),
        target_n           = cfg.get("target_n", 0),
        sampling_technique = sampling_map.get(
            cfg.get("sampling_technique",""), SamplingTechnique.CONSECUTIVE
        ),
    )
    for fac_cfg in cfg.get("facilities", []):
        study.add_facility(Facility(
            id                 = fac_cfg["id"],
            name               = fac_cfg["name"],
            ward               = fac_cfg.get("ward", ""),
            lga                = fac_cfg.get("lga", ""),
            state              = fac_cfg.get("state", ""),
            facility_type      = fac_cfg.get("facility_type", "Primary Health Centre"),
            satisfaction_effect = fac_cfg.get("satisfaction_effect", 0.0),
            notes              = fac_cfg.get("notes", ""),
        ))
    return study


def _build_questionnaire(cfg: dict) -> Questionnaire:
    scale_labels = {int(k): v for k, v in cfg.get("scale", {}).items()}
    instrument   = Questionnaire(
        title       = cfg.get("title", "Questionnaire"),
        study_title = cfg.get("study_title", ""),
        version     = cfg.get("version", "1.0"),
    )
    sections = cfg.get("sections", {})
    for sec_key in sorted(sections.keys()):
        sec_cfg = sections[sec_key]
        section = Section(key=sec_key, title=sec_cfg.get("title", f"Section {sec_key}"))
        for idx, item_text in enumerate(sec_cfg.get("items", []), start=1):
            q_num  = f"{sec_key}{idx}"
            var_nm = f"s{sec_key.lower()}q{idx}"
            q = Question(
                number         = q_num,
                text           = item_text,
                question_type  = QuestionType.LIKERT_5,
                variable_name  = var_nm,
                scale_labels   = scale_labels or None,
            )
            section.add(q)
        instrument.add_section(section)
    return instrument


def _add_questionnaire_variables(vd: VariableDictionary, cfg: dict) -> None:
    """Add one Variable per question item, plus section means and overall mean."""
    scale_labels = {int(k): v for k, v in cfg.get("scale", {}).items()}
    allowed = list(scale_labels.keys()) if scale_labels else [1,2,3,4,5]
    sections = cfg.get("sections", {})

    for sec_key in sorted(sections.keys()):
        sec_cfg = sections[sec_key]
        for idx, item_text in enumerate(sec_cfg.get("items", []), start=1):
            var_nm = f"s{sec_key.lower()}q{idx}"
            vd.add(Variable(
                name           = var_nm,
                label          = item_text,
                scale          = MeasurementScale.ORDINAL,
                data_type      = int,
                section        = sec_key,
                question_number = f"{sec_key}{idx}",
                allowed_values = allowed,
                spss_codes     = {str(v): v for v in allowed},
                notes          = f"Likert item — {cfg.get('title','')}",
            ))
        # Section mean (derived)
        mean_nm = f"mean_{sec_key}"
        if mean_nm not in vd:
            vd.add(Variable(
                name        = mean_nm,
                label       = f"Section {sec_key} mean score ({sec_cfg.get('title','')})",
                scale       = MeasurementScale.SCALE,
                data_type   = float,
                section     = sec_key,
                valid_range = (1.0, 5.0),
                is_derived  = True,
                notes       = "Computed as mean of all items in this section",
            ))

    # Overall mean
    if "overall_mean" not in vd:
        vd.add(Variable(
            name        = "overall_mean",
            label       = "Overall satisfaction mean score",
            scale       = MeasurementScale.SCALE,
            data_type   = float,
            valid_range = (1.0, 5.0),
            is_derived  = True,
        ))
    # Satisfaction category
    if "satisfaction_category" not in vd:
        vd.add(Variable(
            name           = "satisfaction_category",
            label          = "Satisfaction category (derived)",
            scale          = MeasurementScale.ORDINAL,
            data_type      = str,
            allowed_values = ["Highly Dissatisfied","Dissatisfied","Neutral",
                              "Satisfied","Highly Satisfied"],
            spss_codes     = {"Highly Dissatisfied":1,"Dissatisfied":2,"Neutral":3,
                              "Satisfied":4,"Highly Satisfied":5},
            is_derived     = True,
        ))


_DEMO_SCALE_MAP = {
    "normal":       MeasurementScale.SCALE,
    "exponential":  MeasurementScale.SCALE,
    "uniform":      MeasurementScale.SCALE,
}

def _add_demographic_variables(vd: VariableDictionary, cfg: dict) -> None:
    """Infer Variable objects from the demographics config dict."""
    label_map = {
        "age":                    ("Age of respondent (years)",        int),
        "gender":                 ("Gender",                           str),
        "marital_status":         ("Marital status",                   str),
        "education":              ("Highest education level",          str),
        "occupation":             ("Occupation",                       str),
        "income_monthly_naira":   ("Monthly income (Naira)",           str),
        "distance_to_facility_km":("Distance to facility (km)",        float),
        "number_of_children":     ("Number of children",               str),
        "child_age_months":       ("Age of index child (months)",      int),
        "previous_visits":        ("Number of previous visits",        str),
    }
    for field, spec in cfg.items():
        if not isinstance(spec, dict):
            continue
        if field in vd:
            continue
        label, dtype = label_map.get(field, (field.replace("_"," ").title(), str))
        dist = spec.get("distribution")
        if dist in _DEMO_SCALE_MAP:
            mn   = spec.get("min", spec.get("mean", 0))
            mx   = spec.get("max", spec.get("mean", 99))
            vd.add(Variable(
                name        = field,
                label       = label,
                scale       = MeasurementScale.SCALE,
                data_type   = dtype,
                section     = "demographics",
                valid_range = (mn, mx),
            ))
        else:
            # Categorical probability dict
            opts = [str(k) for k in spec.keys() if k != "distribution"]
            if opts:
                vd.add(Variable(
                    name           = field,
                    label          = label,
                    scale          = MeasurementScale.ORDINAL if len(opts) <= 6
                                     else MeasurementScale.NOMINAL,
                    data_type      = dtype,
                    section        = "demographics",
                    allowed_values = opts,
                ))


def _add_observation_variables(vd: VariableDictionary, cfg: dict) -> None:
    """Add Yes/No Variables for each observation checklist item."""
    for item in cfg.get("checklist", []):
        key = item["key"]
        if key in vd:
            continue
        vd.add(Variable(
            name           = key,
            label          = item.get("label", key.replace("_"," ").title()),
            scale          = MeasurementScale.NOMINAL,
            data_type      = str,
            section        = f"observation_{item.get('domain','environment')}",
            allowed_values = ["Yes", "No"],
            spss_codes     = {"Yes": 1, "No": 0},
            notes          = f"Facility observation — {item.get('domain','')}",
        ))
    if cfg.get("checklist") and "obs_yes_count" not in vd:
        n = len(cfg["checklist"])
        vd.add(Variable(
            name        = "obs_yes_count",
            label       = "Total observation checklist items marked Yes",
            scale       = MeasurementScale.SCALE,
            data_type   = int,
            valid_range = (0, n),
            is_derived  = True,
        ))


# ── Helpers ───────────────────────────────────────────────────

def _load_json(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def _assert_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Required study file missing: {path}\n"
            f"Each study directory must contain: "
            f"config.json, questionnaire.json, demographics.json, observation.json"
        )

"""
research_engine/generators/observations.py
Stage 7 — Observation Engine

Generates facility observation (Yes/No checklist) data that is
statistically consistent with respondent satisfaction scores.

Design principle: A researcher who observes a facility on the same day
a respondent visits it should record observations that agree with what
the respondent experienced. This module enforces that consistency.

The probability of "Yes" for each item is anchored to the respondent's
environment section mean (for physical items) or service section mean
(for service/clinical items). Distance affects the waiting-time item.

Public API
----------
    generate(respondents, observation_cfg, rng, env_section, svc_section)
    → list[Respondent]  (Observation objects added in place)

Example
-------
    >>> from research_engine.generators.observations import generate
    >>> generate(respondents, obs_cfg, rng)
    >>> respondents[0].observation_dict["cleanliness"]
    'Yes'
"""
from __future__ import annotations

import numpy as np

from research_engine.models import Respondent, Observation


def generate(
    respondents:      list[Respondent],
    observation_cfg:  dict,
    rng:              np.random.Generator,
    env_section:      str   = "D",
    svc_section:      str   = "B",
    distance_field:   str   = "distance_to_facility_km",
    dist_max:         float = 20.0,
) -> list[Respondent]:
    """
    Add Observation objects to each Respondent.

    The respondents list is mutated in place.

    Parameters
    ----------
    respondents      : Respondent objects with demographics and Likert responses
    observation_cfg  : raw observation.json dict (contains "checklist" list)
    rng              : seeded numpy generator
    env_section      : questionnaire section key for environment (default "D")
    svc_section      : questionnaire section key for service quality (default "B")
    distance_field   : demographic field name for distance to facility
    dist_max         : km above which distance penalty is maxed

    Returns
    -------
    list[Respondent] — same list, mutated in place
    """
    checklist = observation_cfg.get("checklist", [])
    if not checklist:
        return respondents

    for respondent in respondents:
        _generate_for_respondent(
            respondent, checklist, rng, env_section, svc_section,
            distance_field, dist_max,
        )

    return respondents


def _generate_for_respondent(
    respondent:    Respondent,
    checklist:     list[dict],
    rng:           np.random.Generator,
    env_section:   str,
    svc_section:   str,
    distance_field: str,
    dist_max:      float,
) -> None:
    """Generate all observation items for one respondent visit."""
    env_score = respondent.get_value(f"mean_{env_section}", 3.0)
    svc_score = respondent.get_value(f"mean_{svc_section}", 3.0)

    # Normalise section scores from 1–5 → 0–1 (probability anchor)
    base_env = (float(env_score) - 1) / 4
    base_svc = (float(svc_score) - 1) / 4

    dist_km     = float(respondent.demographics.get(distance_field, 2.0))
    dist_factor = min(dist_km / dist_max, 1.0)

    yes_count = 0
    for item in checklist:
        key    = item["key"]
        domain = item.get("domain", "environment")

        if domain == "service":
            p = float(np.clip(base_svc + rng.normal(0, 0.08), 0.05, 0.98))
        else:
            p = float(np.clip(base_env + rng.normal(0, 0.07), 0.05, 0.98))

        # Distance-penalise the waiting-time item specifically
        if "waiting" in key:
            p = float(np.clip(
                base_env - dist_factor * 0.3 + rng.normal(0, 0.06),
                0.05, 0.98
            ))

        value = "Yes" if rng.random() < p else "No"
        if value == "Yes":
            yes_count += 1

        respondent.add_observation(Observation(
            variable_name = key,
            value         = value,
            facility_id   = respondent.facility_id,
        ))

    # Total yes count as an observation
    respondent.add_observation(Observation(
        variable_name = "obs_yes_count",
        value         = str(yes_count),
        facility_id   = respondent.facility_id,
    ))

"""
research_engine/generators/responses.py
Stage 6 — Response Intelligence Engine  ⭐

Generates Likert-scale Response objects that are internally coherent.
This is the most important generator module — it determines whether the
dataset is defensible.

Causal Model
------------
Instead of random numbers, responses follow a configurable causal chain:

    education rank  ──►  base_satisfaction  (higher edu → slightly higher)
    income rank     ──►  base_satisfaction  (smaller effect)
    previous visits ──►  base_satisfaction  (familiarity → higher)
    facility effect ──►  base_satisfaction  (per-facility bias ±0.5)
    distance        ──►  penalty on physical environment + waiting time sections

The base satisfaction is calculated once per respondent. Section-specific
penalties are then applied on top. Gaussian noise is added to each item.
The result is clamped to the valid Likert range [1, 5].

Configurable via the `causal_weights` dict — any weight can be overridden
without changing this module.

Public API
----------
    generate(respondents, questionnaire, rng, facility_effects, causal_weights)
    → list[Respondent]  (respondents are mutated in place — responses added)

Example
-------
    >>> from research_engine.generators.responses import generate
    >>> generate(respondents, questionnaire, rng, facility_effects={1:0.3,2:0.0})
    >>> respondents[0].get_response("saq1").value   # Likert 1–5
    4
"""
from __future__ import annotations

import numpy as np

from research_engine.models import Respondent, Response, Questionnaire


# Default causal weights — override via causal_weights argument
DEFAULT_WEIGHTS: dict = {
    "base":               3.2,    # centre of satisfaction scale (neutral = 3.0)
    "edu_rank":           0.15,   # per unit above rank 2 → +0.15 satisfaction
    "income_rank":        0.08,   # per unit above rank 2 → +0.08 satisfaction
    "visit_rank":         0.12,   # per unit above rank 2 → +0.12 satisfaction
    "distance_max_km":    20,     # distance beyond which penalty is maxed
    "env_penalty":        0.5,    # max penalty on physical environment section
    "e_penalty":          0.6,    # max penalty on section E (overall satisfaction)
    "wait_penalty":       1.0,    # max penalty on the "waiting time" item
    "noise_sd":           0.55,   # standard deviation of item-level Gaussian noise
    "env_section":        "D",    # section key for physical environment
    "final_section":      "E",    # section key for overall/intention-to-return
    "wait_item_offset":   -2,     # position of waiting-time item from end of section E
}


def generate(
    respondents:      list[Respondent],
    questionnaire:    Questionnaire,
    rng:              np.random.Generator,
    facility_effects: dict[int, float] | None = None,
    causal_weights:   dict | None = None,
) -> list[Respondent]:
    """
    Add Response objects to each Respondent based on the causal model.

    The respondents list is mutated in place (responses are added).
    The same list is also returned for chaining.

    Parameters
    ----------
    respondents      : list of Respondent objects (demographics already set)
    questionnaire    : the study instrument (defines sections and items)
    rng              : seeded numpy generator
    facility_effects : {facility_id: float} — per-facility satisfaction bias
    causal_weights   : override any key in DEFAULT_WEIGHTS

    Returns
    -------
    list[Respondent] — same list, mutated in place
    """
    weights = {**DEFAULT_WEIGHTS, **(causal_weights or {})}
    fac_eff = facility_effects or {}

    for respondent in respondents:
        _generate_for_respondent(respondent, questionnaire, rng, fac_eff, weights)

    return respondents


# ── Per-respondent generation ─────────────────────────────────

def _generate_for_respondent(
    respondent:  Respondent,
    instrument:  Questionnaire,
    rng:         np.random.Generator,
    fac_eff:     dict[int, float],
    weights:     dict,
) -> None:
    """Compute base satisfaction and generate all Likert responses."""
    dm = respondent.demographics

    # ── Compute base satisfaction ─────────────────────────────
    base = weights["base"]
    base += (dm.get("education_rank", 2) - 2)           * weights["edu_rank"]
    base += (dm.get("income_monthly_naira_rank", 2) - 2)* weights["income_rank"]
    base += (dm.get("previous_visits_rank", 2) - 2)     * weights["visit_rank"]
    base += fac_eff.get(respondent.facility_id, 0.0)

    dist_km      = float(dm.get("distance_to_facility_km", 2.0))
    dist_factor  = min(dist_km / weights["distance_max_km"], 1.0)

    env_section  = weights["env_section"]
    final_section = weights["final_section"]

    # ── Generate one response per question ────────────────────
    for section in instrument.sections:
        n_items = len(section.questions)
        for item_idx, question in enumerate(section.questions):
            noise   = float(rng.normal(0, weights["noise_sd"]))
            penalty = 0.0

            if section.key == env_section:
                penalty = dist_factor * weights["env_penalty"]

            elif section.key == final_section:
                # The "waiting time" item gets the heaviest penalty
                is_wait = (item_idx == n_items + weights["wait_item_offset"])
                penalty = dist_factor * (
                    weights["wait_penalty"] if is_wait else weights["e_penalty"]
                )

            raw   = base - penalty + noise
            value = _clamp_likert(raw, question)
            respondent.add_response(Response(
                variable_name = question.variable_name,
                value         = value,
            ))

    # ── Compute derived variables ─────────────────────────────
    _add_derived_variables(respondent, instrument)


def _add_derived_variables(
    respondent: Respondent,
    instrument: Questionnaire,
) -> None:
    """
    Add section means, overall mean, and satisfaction category responses.
    These are derived — computed from the Likert item responses.
    """
    section_means: list[float] = []

    for section in instrument.sections:
        var_names = [q.variable_name for q in section.questions]
        mean      = respondent.likert_mean(var_names)
        if mean is not None:
            mean_name = f"mean_{section.key}"
            respondent.add_response(Response(mean_name, round(mean, 2)))
            section_means.append(mean)

    if section_means:
        overall = round(sum(section_means) / len(section_means), 2)
        respondent.add_response(Response("overall_mean", overall))
        respondent.add_response(Response(
            "satisfaction_category",
            _satisfaction_label(overall),
        ))


def _clamp_likert(value: float, question) -> int:
    """Clamp a float to the question's valid Likert integer range."""
    if question.likert_range:
        lo, hi = question.likert_range
    else:
        lo, hi = 1, 5
    return int(np.clip(round(value), lo, hi))


def _satisfaction_label(mean: float) -> str:
    if mean >= 4.5: return "Highly Satisfied"
    if mean >= 3.5: return "Satisfied"
    if mean >= 2.5: return "Neutral"
    if mean >= 1.5: return "Dissatisfied"
    return "Highly Dissatisfied"

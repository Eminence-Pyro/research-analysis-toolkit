"""
rdg/core/questionnaire.py

Generates Likert-scale questionnaire responses (1–5) that are internally
coherent. The causal model is configurable via the driver dict.

Causal model (default, overridable):
  - Higher education rank  → slightly higher satisfaction
  - Higher income rank     → modest effect
  - More previous visits   → familiarity → higher satisfaction
  - Longer distance        → lower satisfaction (sections D, E)
  - Facility fixed effect  → small per-facility bias
"""
from __future__ import annotations
import json
import numpy as np
from pathlib import Path
from typing import Any


def _clamp_likert(val: float) -> int:
    return int(np.clip(round(val), 1, 5))


def generate(
    respondents:         list[dict],
    questionnaire_path:  str | Path,
    rng:                 np.random.Generator,
    facility_assignments: list[int],
    facility_effects:    dict[int, float] | None = None,
    causal_cfg:          dict | None = None,
) -> list[dict[str, Any]]:
    """
    Generate questionnaire response rows correlated with respondent demographics.

    Parameters
    ----------
    respondents           : output of demographics.generate()
    questionnaire_path    : path to questionnaire.json
    rng                   : seeded numpy random generator
    facility_assignments  : list of facility IDs (one per respondent)
    facility_effects      : {facility_id: float} additive effects on base satisfaction
    causal_cfg            : overrides for the causal model weights

    Returns
    -------
    list of dicts — one per respondent, columns SAQ1…SEQ5 + section means + overall
    """
    with open(questionnaire_path) as f:
        q_cfg: dict = json.load(f)

    sections   = q_cfg["sections"]
    section_keys = sorted(sections.keys())
    facility_effects = facility_effects or {}

    # Default causal weights — override via causal_cfg
    weights = {
        "base":          3.2,
        "edu_rank":      0.15,    # per unit of edu_rank above 2
        "income_rank":   0.08,
        "visit_rank":    0.12,
        "distance_max":  20,
        "dist_penalty_D": 0.5,
        "dist_penalty_E": 0.6,
        "dist_penalty_wait": 1.0,
        "noise_sd":      0.55,
    }
    if causal_cfg:
        weights.update(causal_cfg)

    # Build flat list of (section_key, item_label)
    all_items: list[tuple[str, str]] = []
    for sec in section_keys:
        for item in sections[sec]["items"]:
            all_items.append((sec, item))

    results: list[dict] = []

    for i, resp in enumerate(respondents):
        fid  = facility_assignments[i]
        base = weights["base"]
        base += (resp.get("education_rank", 2) - 2) * weights["edu_rank"]
        base += (resp.get("income_rank", 2) - 2)     * weights["income_rank"]
        base += (resp.get("previous_visits_rank", 2) - 2) * weights["visit_rank"]
        base += facility_effects.get(fid, 0)

        dist_factor = min(resp.get("distance_to_facility_km", 2) / weights["distance_max"], 1)

        row: dict[str, Any] = {"respondent_id": resp["respondent_id"]}

        # Track index within each section for item-level effects (e.g., "waiting time" item)
        sec_item_counters: dict[str, int] = {s: 0 for s in section_keys}
        n_items_per_sec   = {s: len(sections[s]["items"]) for s in section_keys}

        for sec, _label in all_items:
            item_idx = sec_item_counters[sec]
            sec_item_counters[sec] += 1

            noise   = rng.normal(0, weights["noise_sd"])
            penalty = 0.0

            if sec == "D":
                penalty = dist_factor * weights["dist_penalty_D"]
            elif sec == "E":
                # Last-but-one item in E is typically "waiting time was acceptable"
                n = n_items_per_sec["E"]
                if item_idx == n - 2:
                    penalty = dist_factor * weights["dist_penalty_wait"]
                else:
                    penalty = dist_factor * weights["dist_penalty_E"]

            col = f"S{sec}Q{item_idx + 1}"
            row[col] = _clamp_likert(base - penalty + noise)

        # Section means
        for sec in section_keys:
            cols = [f"S{sec}Q{j}" for j in range(1, n_items_per_sec[sec] + 1)]
            row[f"mean_{sec}"] = round(float(np.mean([row[c] for c in cols])), 2)

        row["overall_mean"] = round(
            float(np.mean([row[f"mean_{s}"] for s in section_keys])), 2
        )

        m = row["overall_mean"]
        row["satisfaction_category"] = (
            "Highly Satisfied"    if m >= 4.5 else
            "Satisfied"           if m >= 3.5 else
            "Neutral"             if m >= 2.5 else
            "Dissatisfied"        if m >= 1.5 else
            "Highly Dissatisfied"
        )

        results.append(row)

    return results

"""
rdg/core/observation.py

Generates facility observation checklist (Yes/No) data that is
statistically consistent with the questionnaire satisfaction responses.

The probability of "Yes" for each checklist item is anchored to the
respondent's section mean scores, keeping the dataset internally coherent.
"""
from __future__ import annotations
import json
import numpy as np
from pathlib import Path
from typing import Any


def generate(
    respondents:           list[dict],
    questionnaire_rows:    list[dict],
    facility_assignments:  list[int],
    observation_path:      str | Path,
    rng:                   np.random.Generator,
    env_section:           str = "D",
    svc_section:           str = "B",
    distance_field:        str = "distance_to_facility_km",
    dist_max:              float = 20,
) -> list[dict[str, Any]]:
    """
    Parameters
    ----------
    respondents          : demographic rows
    questionnaire_rows   : questionnaire response rows (for score anchoring)
    facility_assignments : facility ID per respondent
    observation_path     : path to observation.json checklist config
    rng                  : seeded generator
    env_section          : questionnaire section key representing environment (default D)
    svc_section          : questionnaire section key representing service quality (default B)
    distance_field       : demographic field name for distance (affects waiting time)

    Returns
    -------
    list of dicts with Yes/No per checklist item + obs_yes_count
    """
    with open(observation_path) as f:
        obs_cfg: dict = json.load(f)
    checklist = obs_cfg["checklist"]

    q_map = {r["respondent_id"]: r for r in questionnaire_rows}

    results: list[dict] = []
    for i, resp in enumerate(respondents):
        rid = resp["respondent_id"]
        q   = q_map[rid]

        env_score = q.get(f"mean_{env_section}", 3.0)
        svc_score = q.get(f"mean_{svc_section}", 3.0)
        base_env  = (env_score - 1) / 4          # normalise 1–5 → 0–1
        base_svc  = (svc_score - 1) / 4
        dist_factor = min(resp.get(distance_field, 2) / dist_max, 1)

        row: dict[str, Any] = {
            "respondent_id": rid,
            "facility_id":   facility_assignments[i],
        }

        for item in checklist:
            key    = item["key"]
            domain = item.get("domain", "environment")

            if domain == "service":
                p = np.clip(base_svc + rng.normal(0, 0.08), 0.05, 0.98)
            else:
                p = np.clip(base_env + rng.normal(0, 0.07), 0.05, 0.98)

            # Waiting time item: distance-penalised
            if "waiting" in key:
                p = np.clip(base_env - dist_factor * 0.3 + rng.normal(0, 0.06), 0.05, 0.98)

            row[key] = "Yes" if rng.random() < p else "No"

        row["obs_yes_count"] = sum(1 for item in checklist if row[item["key"]] == "Yes")
        results.append(row)

    return results

"""
research_engine/generators/demographics.py
Stage 5 — Synthetic Population Generator

Creates Respondent objects with realistic demographic profiles.

This module replaces the old rdg/core/demographics.py. Instead of
returning a list of plain dicts, it returns a list of Respondent
domain objects with demographics populated from a config dict.

The demographics config is the raw dict from demographics.json —
the same format used by the json_loader. This module is therefore
completely study-agnostic: it reads whatever distributions are in the
config and generates accordingly.

Public API
----------
    generate(n, demographics_cfg, facility_assignments, rng, ordinal_maps)
    → list[Respondent]

Example
-------
    >>> import numpy as np
    >>> from research_engine.generators.demographics import generate
    >>> import json
    >>> cfg = json.load(open("studies/immunization_aba/demographics.json"))
    >>> rng = np.random.default_rng(42)
    >>> respondents = generate(120, cfg, [1]*30+[2]*30+[3]*30+[4]*30, rng)
    >>> respondents[0].respondent_id
    'R001'
    >>> respondents[0].demographics["gender"]
    'Female'
"""
from __future__ import annotations

from typing import Any
import numpy as np

from research_engine.models import Respondent


def generate(
    n:                    int,
    demographics_cfg:     dict,
    facility_assignments: list[int],
    rng:                  np.random.Generator,
    ordinal_maps:         dict[str, dict[str, int]] | None = None,
    id_prefix:            str = "R",
    id_width:             int = 3,
) -> list[Respondent]:
    """
    Generate n Respondent objects with demographics drawn from config distributions.

    Parameters
    ----------
    n                    : number of respondents to generate
    demographics_cfg     : raw demographics.json dict — field → distribution spec
    facility_assignments : list of facility IDs, length must equal n
    rng                  : seeded numpy random generator (for reproducibility)
    ordinal_maps         : optional dict mapping field name → {label: rank_int}
                           Adds a "<field>_rank" int to each respondent's demographics.
                           Example: {"education": {"Primary":1,"Secondary":2,"Tertiary":3}}
    id_prefix            : prefix for respondent IDs (default "R")
    id_width             : zero-padding width for ID number (default 3 → "R001")

    Returns
    -------
    list[Respondent] — one per respondent, in order
    """
    if len(facility_assignments) != n:
        raise ValueError(
            f"facility_assignments length ({len(facility_assignments)}) "
            f"must equal n ({n})."
        )

    respondents: list[Respondent] = []

    for i in range(n):
        rid          = f"{id_prefix}{i + 1:0{id_width}d}"
        facility_id  = facility_assignments[i]
        demographics = _draw_demographics(demographics_cfg, rng)

        # Add ordinal rank columns if maps provided
        if ordinal_maps:
            for field, mapping in ordinal_maps.items():
                if field in demographics:
                    demographics[f"{field}_rank"] = mapping.get(
                        str(demographics[field]), 0
                    )

        respondents.append(
            Respondent(
                respondent_id = rid,
                facility_id   = facility_id,
                demographics  = demographics,
            )
        )

    return respondents


# ── Internal helpers ──────────────────────────────────────────

def _draw_demographics(cfg: dict, rng: np.random.Generator) -> dict[str, Any]:
    """Draw one respondent's demographic values from the config distributions."""
    demographics: dict[str, Any] = {}

    for field, spec in cfg.items():
        if not isinstance(spec, dict):
            continue
        dist = spec.get("distribution")

        if dist == "normal":
            val = float(np.clip(
                rng.normal(spec["mean"], spec["std"]),
                spec["min"], spec["max"]
            ))
            demographics[field] = int(val) if _is_integer_field(field) else round(val, 1)

        elif dist == "exponential":
            val = float(np.clip(
                rng.exponential(spec["scale"]),
                spec["min"], spec["max"]
            ))
            demographics[field] = round(val, 1)

        elif dist == "uniform":
            val = float(rng.uniform(spec["min"], spec["max"] + 1))
            demographics[field] = int(val)

        else:
            # Categorical probability dict — keys are labels, values are probabilities
            options = {k: v for k, v in spec.items() if k != "distribution"}
            demographics[field] = _weighted_choice(options, rng)

    return demographics


def _weighted_choice(options: dict[str, float], rng: np.random.Generator) -> str:
    """Draw one label from a probability dict, normalising probabilities."""
    keys  = list(options.keys())
    probs = [float(v) for v in options.values()]
    total = sum(probs)
    probs = [p / total for p in probs]          # normalise to exactly 1.0
    return str(rng.choice(keys, p=probs))


_INTEGER_FIELDS = {"age", "child_age_months", "n_children", "number_of_children"}

def _is_integer_field(field: str) -> bool:
    return field in _INTEGER_FIELDS or field.endswith(("_age","_months","_years","_count"))

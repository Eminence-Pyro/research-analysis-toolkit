"""
rdg/core/demographics.py

Generic caregiver / respondent demographics generator.
Reads a demographics.json config file and produces a list of respondent dicts.
Works for any study — just swap the config file.
"""
from __future__ import annotations
import json
import numpy as np
from pathlib import Path
from typing import Any


def _weighted_choice(options: dict[str, float], rng: np.random.Generator) -> str:
    keys  = list(options.keys())
    probs = list(options.values())
    # Normalise in case floats don't sum to exactly 1.0
    total = sum(probs)
    probs = [p / total for p in probs]
    return str(rng.choice(keys, p=probs))


def generate(
    n: int,
    config_path: str | Path,
    rng: np.random.Generator,
    ordinal_maps: dict[str, dict[str, int]] | None = None,
) -> list[dict[str, Any]]:
    """
    Generate n respondent demographic records.

    Parameters
    ----------
    n            : number of respondents
    config_path  : path to demographics.json for this study
    rng          : seeded numpy random generator
    ordinal_maps : optional dict mapping categorical fields to numeric rank codes
                   e.g. {"education": {"Primary":1, "Secondary":2, "Tertiary":3}}
                   These become extra numeric columns (field + "_rank") in each row.

    Returns
    -------
    list of dicts — one per respondent
    """
    with open(config_path) as f:
        cfg: dict = json.load(f)

    respondents: list[dict] = []

    for i in range(n):
        row: dict[str, Any] = {"respondent_id": f"R{i + 1:03d}"}

        for field, spec in cfg.items():
            if not isinstance(spec, dict):
                continue

            dist = spec.get("distribution")

            if dist == "normal":
                val = float(np.clip(
                    rng.normal(spec["mean"], spec["std"]),
                    spec["min"], spec["max"]
                ))
                row[field] = int(val) if field.endswith(("age", "months", "years")) else round(val, 1)

            elif dist == "exponential":
                val = float(np.clip(
                    rng.exponential(spec["scale"]),
                    spec["min"], spec["max"]
                ))
                row[field] = round(val, 1)

            elif dist == "uniform":
                val = float(rng.uniform(spec["min"], spec["max"] + 1))
                row[field] = int(val)

            else:
                # Treat as categorical probability dict
                numeric_keys = all(
                    str(k).replace(".", "").replace("-", "").lstrip("-").isdigit()
                    for k in spec
                    if k != "distribution"
                )
                row[field] = _weighted_choice(spec, rng)

        # Add ordinal rank columns if requested
        if ordinal_maps:
            for field, mapping in ordinal_maps.items():
                if field in row:
                    row[f"{field}_rank"] = mapping.get(str(row[field]), 0)

        respondents.append(row)

    return respondents

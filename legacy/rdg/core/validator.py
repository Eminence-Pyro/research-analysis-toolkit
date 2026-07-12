"""
rdg/core/validator.py

Runs statistical and logical consistency checks before export.
All checks produce machine-readable results — callers decide how to display them.
"""
from __future__ import annotations
import numpy as np
from collections import Counter
from typing import Any


ValidationReport = dict[str, list | dict]


def run(
    demographics:        list[dict],
    questionnaire_rows:  list[dict],
    observations:        list[dict],
    expected_n:          int | None = None,
    edu_rank_field:      str = "education_rank",
    distance_field:      str = "distance_to_facility_km",
    env_section:         str = "D",
    svc_section:         str = "B",
) -> ValidationReport:
    """
    Run all validation checks and return a structured report.

    Returns
    -------
    dict with keys: "passed", "warnings", "errors", "summary"
    """
    passed:   list[str] = []
    warnings: list[str] = []
    errors:   list[str] = []
    n = len(demographics)

    # ── 1. Sample size ──────────────────────────────────────
    min_n = expected_n or 100
    if n >= min_n:
        passed.append(f"Sample size: {n} respondents (≥{min_n} ✓)")
    else:
        errors.append(f"Sample size {n} is below expected {min_n}")

    # ── 2. Unique IDs ───────────────────────────────────────
    ids = [r["respondent_id"] for r in demographics]
    if len(set(ids)) == n:
        passed.append("All respondent IDs are unique")
    else:
        errors.append(f"Duplicate respondent IDs: {n - len(set(ids))} duplicates found")

    # ── 3. Likert range ──────────────────────────────────────
    likert_cols = [k for k in questionnaire_rows[0] if k.startswith("S") and "Q" in k]
    bad = [
        (r["respondent_id"], col, r[col])
        for r in questionnaire_rows
        for col in likert_cols
        if not (1 <= r[col] <= 5)
    ]
    if not bad:
        passed.append(f"All {len(likert_cols)} Likert items within valid 1–5 range")
    else:
        errors.append(f"Out-of-range Likert values ({len(bad)}): {bad[:3]}…")

    # ── 4. Education → satisfaction (positive correlation expected) ──
    edu_ranks = [r.get(edu_rank_field, 0) for r in demographics]
    sat_means = [r["overall_mean"] for r in questionnaire_rows]
    if any(edu_ranks):
        corr = float(np.corrcoef(edu_ranks, sat_means)[0, 1])
        if corr > 0:
            passed.append(f"Education–satisfaction correlation: r={corr:.3f} (positive ✓)")
        else:
            warnings.append(f"Education–satisfaction correlation negative: r={corr:.3f}")

    # ── 5. Distance → satisfaction (negative correlation expected) ──
    distances = [r.get(distance_field, 0) for r in demographics]
    if any(distances):
        dist_corr = float(np.corrcoef(distances, sat_means)[0, 1])
        if dist_corr < 0:
            passed.append(f"Distance–satisfaction correlation: r={dist_corr:.3f} (negative ✓)")
        else:
            warnings.append(f"Distance–satisfaction correlation positive: r={dist_corr:.3f}")

    # ── 6. Observation–environment consistency ───────────────
    env_means  = [q.get(f"mean_{env_section}", 3) for q in questionnaire_rows]
    obs_counts = [o["obs_yes_count"] for o in observations]
    obs_corr   = float(np.corrcoef(env_means, obs_counts)[0, 1])
    if obs_corr > 0:
        passed.append(f"Observation–environment consistency: r={obs_corr:.3f} (positive ✓)")
    else:
        warnings.append(f"Observation data inconsistent with environment scores: r={obs_corr:.3f}")

    # ── 7. No missing data in questionnaire ──────────────────
    missing = sum(1 for r in questionnaire_rows for col in likert_cols if r.get(col) is None)
    if missing == 0:
        passed.append("No missing values in questionnaire items")
    else:
        errors.append(f"{missing} missing questionnaire values detected")

    # ── 8. Satisfaction category distribution ────────────────
    cats = Counter(q["satisfaction_category"] for q in questionnaire_rows)
    passed.append(f"Satisfaction categories: {dict(cats)}")

    # ── 9. Per-section mean summaries ────────────────────────
    section_keys = sorted({k.split("_")[1] for k in questionnaire_rows[0] if k.startswith("mean_")})
    for sec in section_keys:
        vals = [q[f"mean_{sec}"] for q in questionnaire_rows]
        passed.append(f"Section {sec}: mean={np.mean(vals):.2f}, SD={np.std(vals):.2f}")

    # ── 10. Impossible value checks ──────────────────────────
    for d in demographics:
        age = d.get("age", 20)
        if not (10 <= age <= 80):
            errors.append(f"Impossible age {age} for {d['respondent_id']}")
            break

    return {
        "passed":   passed,
        "warnings": warnings,
        "errors":   errors,
        "summary": {
            "n_passed":        len(passed),
            "n_warnings":      len(warnings),
            "n_errors":        len(errors),
            "ready_to_export": len(errors) == 0,
        },
    }

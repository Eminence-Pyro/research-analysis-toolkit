"""
studies/immunization_aba/run.py

Study runner for:
  "Pattern of Caregiver Satisfaction with Immunization Services
   at Urban PHCs, Wards I-IV, Aba North LGA, Abia State"

This file wires together the research_engine domain layer:
  1. json_loader   → Study, Questionnaire, VariableDictionary
  2. generators    → Respondents, Responses, Observations  → Dataset
  3. validators    → ValidationReport
  4. exporters     → Excel, CSV, SPSS  (Stage 10 — wired when ready)

To adapt this runner for a different study, copy this folder, rename it,
replace the JSON config files, and update ORDINAL_MAPS and SPSS_MAPS.
No changes to research_engine/ are needed.
"""
from __future__ import annotations
from pathlib import Path
import time
import numpy as np

from research_engine.parsers    import load_all
from research_engine.generators import (
    generate_respondents, generate_responses, generate_observations,
)
from research_engine.models     import Dataset
from research_engine.validators import validate

STUDY_DIR  = Path(__file__).parent
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output" / "immunization_aba"

# Ordinal rank maps — must match the categories in demographics.json
ORDINAL_MAPS = {
    "education": {
        "No formal education": 1, "Primary": 2,
        "Secondary": 3, "Tertiary": 4,
    },
    "income_monthly_naira": {
        "No income (<10,000)": 1, "Low (10,000-30,000)": 2,
        "Middle (30,001-70,000)": 3, "High (>70,000)": 4,
    },
    "previous_visits": {
        "1 (first visit)": 1, "2-3": 2, "4-5": 3, "6+": 4,
    },
}


def run(seed: int = 42) -> None:
    """
    Run the full generation pipeline for this study.
    Pass a different seed to regenerate a statistically equivalent dataset.
    """
    _banner()
    rng = np.random.default_rng(seed)

    # ── Step 1: Load study from JSON configs ─────────────────
    _step(1, 5, "Loading study configuration")
    t      = time.time()
    bundle = load_all(STUDY_DIR)
    study  = bundle.study
    q      = bundle.questionnaire
    vd     = bundle.variable_dictionary
    print(f"     {study.title}")
    print(f"     {study.n_facilities} facilities, target n={study.target_n}")
    print(f"     {q.question_count} questions across {len(q.sections)} sections")
    print(f"     {len(vd)} variables in dictionary  ({time.time()-t:.1f}s)")

    # ── Step 2: Generate respondents (demographics) ───────────
    _step(2, 5, "Generating study population")
    t = time.time()
    respondents = generate_respondents(
        n                    = study.target_n,
        demographics_cfg     = bundle.raw_demographics,
        facility_assignments = study.facility_assignments(),
        rng                  = rng,
        ordinal_maps         = ORDINAL_MAPS,
    )
    print(f"     {len(respondents)} respondents created  ({time.time()-t:.1f}s)")
    _show_sample(respondents[0])

    # ── Step 3: Generate questionnaire responses ──────────────
    _step(3, 5, "Generating responses (causal model)")
    t = time.time()
    fac_effects = {f.id: f.satisfaction_effect for f in study.facilities}
    generate_responses(respondents, q, rng, facility_effects=fac_effects)
    print(f"     {q.question_count} items × {len(respondents)} respondents  ({time.time()-t:.1f}s)")

    # ── Step 4: Generate observation checklist ────────────────
    _step(4, 5, "Generating facility observations")
    t = time.time()
    generate_observations(respondents, bundle.raw_observation, rng)
    obs_items = len(bundle.raw_observation.get("checklist", []))
    print(f"     {obs_items} items × {len(respondents)} visits  ({time.time()-t:.1f}s)")

    # ── Step 5: Build Dataset and validate ────────────────────
    _step(5, 5, "Building dataset and validating")
    t      = time.time()
    dataset = Dataset(study_title=study.title, seed=seed)
    for resp in respondents:
        dataset.add(resp)

    report = validate(dataset, study)
    s      = report.summary()
    print(f"     {s}  ({time.time()-t:.1f}s)")

    if not report.is_ready:
        print("\n  ✗ Validation failed. Errors:")
        for e in report.errors:
            print(f"     • {e.message}")
        return

    # ── Print validation detail ───────────────────────────────
    print()
    for check in report.checks:
        icon = {"pass": "  ✓", "warn": "  ⚠", "error": "  ✗"}[check.status]
        print(f"{icon}  {check.message}")

    print()
    print(f"  Dataset ready. {len(dataset)} respondents, {len(dataset.variable_names)} variables.")
    print(f"  Export (Stage 10) will write to: {OUTPUT_DIR}/")
    print()


def _banner():
    print(f"\n{'─'*60}")
    print("  RESEARCH ANALYSIS TOOLKIT")
    print("  Study: Caregiver Satisfaction — Immunization Services")
    print(f"{'─'*60}")


def _step(n, total, label):
    print(f"\n  [{n}/{total}] {label}")


def _show_sample(r):
    dm = r.demographics
    print(f"     Sample respondent: {r.respondent_id} | "
          f"Facility {r.facility_id} | "
          f"Age {dm.get('age','?')} | "
          f"Gender {dm.get('gender','?')} | "
          f"Edu {dm.get('education','?')} | "
          f"Dist {dm.get('distance_to_facility_km','?')} km")

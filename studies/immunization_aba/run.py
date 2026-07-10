"""
studies/immunization_aba/run.py

Complete study runner — Stages 2 through 10.
Loads → Generates → Validates → Analyses → Exports.

Usage
-----
    python main.py --study immunization_aba
    python main.py --study immunization_aba --seed 123
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
from research_engine.exporters  import export_excel, export_raw_csv, export_spss

STUDY_DIR  = Path(__file__).parent
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output" / "immunization_aba"

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

SPSS_MAPS = {
    "gender":          {"Male": 1, "Female": 2},
    "marital_status":  {"Married": 1, "Single": 2, "Widowed": 3, "Divorced/Separated": 4},
    "education":       {"No formal education": 1, "Primary": 2, "Secondary": 3, "Tertiary": 4},
    "occupation":      {"Trader/Business": 1, "Civil servant": 2, "Housewife": 3,
                        "Student": 4, "Artisan": 5, "Unemployed": 6},
    "income_monthly_naira": {
        "No income (<10,000)": 1, "Low (10,000-30,000)": 2,
        "Middle (30,001-70,000)": 3, "High (>70,000)": 4,
    },
    "number_of_children": {"1": 1, "2": 2, "3": 3, "4": 4, "5+": 5},
    "previous_visits":    {"1 (first visit)": 1, "2-3": 2, "4-5": 3, "6+": 4},
    "satisfaction_category": {
        "Highly Dissatisfied": 1, "Dissatisfied": 2, "Neutral": 3,
        "Satisfied": 4, "Highly Satisfied": 5,
    },
}

CROSSTAB_PAIRS = [
    ("gender",            "satisfaction_category"),
    ("education",         "satisfaction_category"),
    ("marital_status",    "satisfaction_category"),
    ("occupation",        "satisfaction_category"),
]


def run(seed: int = 42) -> None:
    _banner()
    rng = np.random.default_rng(seed)

    # ── 1. Load ───────────────────────────────────────────────
    _step(1, 7, "Loading study configuration")
    t      = time.time()
    bundle = load_all(STUDY_DIR)
    study  = bundle.study
    q      = bundle.questionnaire
    vd     = bundle.variable_dictionary
    print(f"     {study.title}")
    print(f"     {study.n_facilities} facilities · n={study.target_n} · "
          f"{q.question_count} questions · {len(vd)} variables  ({time.time()-t:.1f}s)")

    # ── 2. Generate respondents ────────────────────────────────
    _step(2, 7, "Generating study population")
    t = time.time()
    respondents = generate_respondents(
        n=study.target_n,
        demographics_cfg=bundle.raw_demographics,
        facility_assignments=study.facility_assignments(),
        rng=rng,
        ordinal_maps=ORDINAL_MAPS,
    )
    print(f"     {len(respondents)} respondents  ({time.time()-t:.1f}s)")

    # ── 3. Generate responses ──────────────────────────────────
    _step(3, 7, "Generating responses (causal model)")
    t = time.time()
    fac_effects = {f.id: f.satisfaction_effect for f in study.facilities}
    generate_responses(respondents, q, rng, facility_effects=fac_effects)
    print(f"     {q.question_count} items × {len(respondents)} respondents  ({time.time()-t:.1f}s)")

    # ── 4. Generate observations ───────────────────────────────
    _step(4, 7, "Generating facility observations")
    t = time.time()
    generate_observations(respondents, bundle.raw_observation, rng)
    obs_items = len(bundle.raw_observation.get("checklist", []))
    print(f"     {obs_items} checklist items × {len(respondents)} visits  ({time.time()-t:.1f}s)")

    # ── 5. Build Dataset + Validate ────────────────────────────
    _step(5, 7, "Building dataset and validating")
    t = time.time()
    dataset = Dataset(study_title=study.title, seed=seed)
    for resp in respondents:
        dataset.add(resp)
    report = validate(dataset, study)
    print(f"     {report.summary()}  ({time.time()-t:.1f}s)")
    for check in report.checks:
        icon = {"pass": "  ✓", "warn": "  ⚠", "error": "  ✗"}[check.status]
        print(f"{icon}  {check.message}")

    if not report.is_ready:
        print("\n  ✗ Validation failed. Aborting export.")
        return

    # ── 6. Export Excel ────────────────────────────────────────
    _step(6, 7, "Exporting Excel workbook (9 sheets)")
    t = time.time()
    xl_path = export_excel(
        dataset             = dataset,
        questionnaire       = q,
        variable_dictionary = vd,
        validation_report   = report,
        output_dir          = OUTPUT_DIR,
        study_title         = study.title,
        seed                = seed,
        spss_maps           = SPSS_MAPS,
        crosstab_pairs      = CROSSTAB_PAIRS,
    )
    print(f"     {xl_path.name}  ({time.time()-t:.1f}s)")

    # ── 7. Export CSV files ────────────────────────────────────
    _step(7, 7, "Exporting CSV files (raw + SPSS-ready)")
    t = time.time()
    raw_path  = export_raw_csv(dataset, OUTPUT_DIR, study.title)
    spss_path = export_spss(dataset, OUTPUT_DIR, SPSS_MAPS, vd, study.title)
    print(f"     {raw_path.name}")
    print(f"     {spss_path.name}")
    print(f"     ({time.time()-t:.1f}s)")

    # ── Done ───────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print(f"  ✓  Complete")
    print(f"  ✓  {len(dataset)} respondents · {len(dataset.variable_names)} variables")
    print(f"  ✓  Output: {OUTPUT_DIR}/")
    print(f"{'─'*60}\n")


def _banner():
    print(f"\n{'─'*60}")
    print("  RESEARCH ANALYSIS TOOLKIT  v1.0")
    print("  Study: Caregiver Satisfaction — Immunization Services")
    print("  Aba North LGA, Abia State")
    print(f"{'─'*60}")

def _step(n, total, label):
    print(f"\n  [{n}/{total}] {label}")

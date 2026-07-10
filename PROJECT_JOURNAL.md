# PROJECT_JOURNAL.md
## Research Dataset Generator — Living Development Log

> Updated after every significant change. Records architectural decisions,
> bugs, lessons learned, and stage outcomes.

---

## Entry #001 — Stage 1: Project Inception

**Date:** July 2026
**Status:** ✅ Complete

### Objective
Build a reusable Python tool for generating statistically coherent,
analysis-ready synthetic datasets for academic research.

### Why This Exists
Generating research data manually is:
- Time consuming
- Inconsistent in coding
- Prone to unrealistic variable relationships
- Difficult to reproduce or modify

This project solves those problems with a repeatable, configurable pipeline.

### Architecture Decisions

**Study-agnostic core (`rdg/core/`)**
All generator modules are completely study-agnostic. They accept config
file paths and parameters — they do not hardcode any study details.
This means any future study can reuse 100% of the core with zero changes.

**Study packages (`studies/<study_name>/`)**
Each study is an isolated package containing:
- `config.py`  — study constants (N, facilities, title, etc.)
- `run.py`     — wires core modules together with study-specific settings
- `demographics.json` — demographic distributions for this population
- `questionnaire.json` — Likert questionnaire sections and items
- `observation.json`  — facility observation checklist items

**Causal model**
Responses are not randomly generated — they follow a realistic causal chain:
  Education level → understanding of services → satisfaction
  Distance to facility → waiting time → lower satisfaction
  Previous visits → familiarity → higher satisfaction
  Facility fixed effects → between-facility variation

The causal weights are configurable via `causal_cfg` dict in the runner.

**SPSS export**
All categorical variables are dual-encoded: raw labels in CSV/Excel,
numeric SPSS codes in the SPSS-ready CSV. Codebook documents every mapping.

### First Study Implemented
`studies/immunization_aba` — Caregiver Satisfaction with Immunization Services,
Urban PHCs, Wards I–IV, Aba North LGA, Abia State. N=120.

### Validation Results (Seed 42)
- 13/13 checks passed, 0 warnings, 0 errors
- Education–satisfaction: r=0.632 (positive ✓)
- Distance–satisfaction: r=-0.117 (negative ✓)
- Observation–environment consistency: r=0.492 (positive ✓)
- Gender: 81.7% female (realistic for immunization settings ✓)

---

## How to Add a New Study

1. Copy `studies/immunization_aba/` to `studies/<your_study>/`
2. Update `config.py` with your study title, N, facilities.
3. Edit `demographics.json` with your population's distributions.
4. Edit `questionnaire.json` with your instrument sections and items.
5. Edit `observation.json` if your study has an observation checklist.
6. Update `run.py` ordinal maps, SPSS maps, and codebook to match.
7. Run: `python main.py --study <your_study>`

No changes to `rdg/core/` are needed.

---

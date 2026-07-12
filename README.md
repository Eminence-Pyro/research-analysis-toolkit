# Research Analysis Toolkit (RAT)

> A Python framework for generating, validating, and exporting statistically coherent
> synthetic research datasets — from questionnaire design to formatted Excel output,
> in a single command.

[![Version](https://img.shields.io/badge/version-1.1.0--dev-orange)](#)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](#)
[![License](https://img.shields.io/badge/license-MIT-green)](#)
[![Stable](https://img.shields.io/badge/stable-v1.0.0-brightgreen)](https://github.com/Eminence-Pyro/research-analysis-toolkit/releases/tag/v1.0.0)

---

## What It Does

The toolkit takes a study defined in JSON configuration files and produces:

- A **9-sheet Excel workbook** — raw data, demographics, Likert responses, facility observations,
  descriptive statistics, frequency tables, cross-tabulations, codebook, and validation report
- A **raw CSV** with labelled values
- An **SPSS-ready CSV** with numeric codes and a companion label file

Data is generated using a **causal response model** — not random values. Education level,
distance to facility, and prior visit history influence satisfaction scores in ways that
match the research literature, making the output academically defensible.

---

## Quick Start

```bash
git clone https://github.com/Eminence-Pyro/research-analysis-toolkit.git
cd research-analysis-toolkit
pip install -r requirements.txt

python main.py run --study immunization_aba
```

Output lands in `output/immunization_aba/` in about 1.5 seconds.

---

## CLI

```bash
python main.py run      --study STUDY [--seed N] [--output DIR]
python main.py list
python main.py info     --study STUDY
python main.py validate --study STUDY [--seed N]
python main.py sample   --population N [--confidence 0.95] [--margin 0.05]
```

---

## Feature Status

✅ = implemented · 🔄 = in progress (v1.1) · 📋 = planned (v2)

| Feature | Status |
|---------|--------|
|---------|--------|
| Domain model (Study, Questionnaire, Respondent, Dataset) | ✅ |
| JSON study config loader | ✅ |
| Causal response model | ✅ |
| 14-check validation engine | ✅ |
| Frequency tables, descriptive statistics, cross-tabulation + χ² | ✅ |
| 9-sheet Excel export, raw CSV, SPSS CSV | ✅ |
| CLI (run, list, info, validate, sample) | ✅ |
| Workflow / orchestration layer (`Pipeline`) | ✅ |
| Plugin registry | ✅ |
| Schema versioning | ✅ |
| Word (.docx) questionnaire parser | 🔄 |
| Chapter Four .docx export | 🔄 |
| SPSS syntax (.sps) generator | 🔄 |
| Cronbach's alpha reliability analysis | 🔄 |
| AI-assisted questionnaire interpretation | 📋 |
| Chart generation, PDF report | 📋 |
| Web dashboard (Streamlit), REST API | 📋 |
| Multiple study designs (cohort, KAP, prevalence) | 📋 |

---

## Tests

```bash
python -m pytest tests/ -v
```

Tests mirror the `research_engine/` structure — `tests/models/`, `tests/workflow/`, etc.

---

## Adding a Study

1. Create `studies/your_study/`
2. Add four JSON files: `config.json`, `questionnaire.json`, `demographics.json`, `observation.json`
3. Set `"schema_version": "1.0"` in `config.json`
4. Copy `studies/immunization_aba/run.py` → update maps → run

No changes to `research_engine/` are ever needed to add a new study.

---

## Documentation

| | |
|-|-|
| [Architecture & Design](docs/architecture.md) | Module map, pipeline, causal model, data flow, plugin system |
| [Study Schema Reference](docs/study-schema.md) | JSON config format for all four study files |
| [Contributing](docs/contributing.md) | Where to work, code standards, how to write a plugin |
| [Project Journal](PROJECT_JOURNAL.md) | Full development history and design decisions |
| [Learning Journal](LEARNING_JOURNAL.md) | Engineering lessons from v0 → v1 |
| [Changelog](CHANGELOG.md) | Version history |
| [ROADMAP](ROADMAP.md) | Master plan, frozen architecture, v1.1 milestones, v2 vision |

---

## Current Study

**Pattern of Caregiver Satisfaction with Immunization Services**
Cross-sectional · Aba North LGA, Abia State · N=120 · 25 Likert items · 58 variables

---

## Dependencies

```
numpy>=1.24.0 · openpyxl>=3.1.0 · scipy>=1.11.0
```

---

## License

MIT

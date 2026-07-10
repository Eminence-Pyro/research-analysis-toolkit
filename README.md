# Research Analysis Toolkit (RAT)

> **Synthetic Research Dataset Generator & Statistical Analysis Engine**
>
> Build statistically valid, reproducible datasets for academic research
> — from questionnaire design to formatted Excel output — in a single command.

[![Version](https://img.shields.io/badge/version-1.0.0-blue)](#)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](#)
[![License](https://img.shields.io/badge/license-MIT-green)](#)
[![Status](https://img.shields.io/badge/status-stable-brightgreen)](#)

---

## What This Is

The Research Analysis Toolkit is a Python framework for generating, validating,
and exporting synthetic research datasets that are statistically coherent and
academically defensible.

It was built to support health-science research projects where:

- The study design and instrument are finalised but data collection is ongoing
- A complete, realistic dataset is needed for analysis planning and code testing
- Outputs must match SPSS/Excel formats expected by supervisors and examiners

**The full pipeline runs in one command:**

```bash
python main.py run --study immunization_aba
```

**Output produced in ~1.5 seconds:**
- A 9-sheet formatted Excel workbook (demographics, Likert data, descriptives,
  frequency tables, crosstabulations, codebook, validation report)
- A raw CSV (all labelled values)
- An SPSS-ready CSV (numeric codes, 8-char column names) + label file

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/Eminence-Pyro/research-analysis-toolkit.git
cd research-analysis-toolkit

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the immunization study (seed=42 for reproducibility)
python main.py run --study immunization_aba

# 4. Find your files
ls output/immunization_aba/
```

---

## CLI Commands

```
python main.py run      --study STUDY [--seed N] [--output DIR]
python main.py list
python main.py info     --study STUDY
python main.py validate --study STUDY [--seed N]
python main.py sample   --population N [--confidence 0.95] [--margin 0.05]
```

| Command | What it does |
|---------|-------------|
| `run` | Full pipeline: load → generate → validate → analyse → export |
| `list` | List all study folders in `studies/` |
| `info` | Print study metadata (design, facilities, questionnaire structure) |
| `validate` | Generate data and run all validation checks — no export |
| `sample` | Compute Cochran / Yamane / Krejcie-Morgan sample size recommendations |

### Examples

```bash
# Run with a different seed
python main.py run --study immunization_aba --seed 123

# Custom output directory
python main.py run --study immunization_aba --output ./my_results

# Just validate — no files written
python main.py validate --study immunization_aba

# Sample size for a known population of 800, 99% confidence
python main.py sample --population 800 --confidence 0.99

# Sample size for unknown population
python main.py sample
```

---

## Project Architecture

```
research-analysis-toolkit/
│
├── main.py                          ← Single CLI entry point
├── requirements.txt
│
├── research_engine/                 ← Core library
│   ├── models/                      ← Stage 1: Domain model
│   │   ├── variable.py              ← Variable, VariableDictionary, MeasurementScale
│   │   ├── questionnaire.py         ← Question, Section, Questionnaire
│   │   ├── study.py                 ← Study, Facility, StudyDesign
│   │   ├── respondent.py            ← Respondent, Response, Observation
│   │   └── dataset.py               ← Dataset
│   │
│   ├── parsers/                     ← Stage 2: Readers
│   │   ├── json_loader.py           ← load_all() → StudyBundle
│   │   └── workbook_reader.py       ← Excel framework reader
│   │
│   ├── generators/                  ← Stages 3–7: Data generation
│   │   ├── sample_size.py           ← Cochran, Yamane, Krejcie-Morgan
│   │   ├── demographics.py          ← Synthetic respondent demographics
│   │   ├── responses.py             ← Likert responses (causal model) ⭐
│   │   └── observations.py          ← Facility observation checklists
│   │
│   ├── validators/                  ← Stage 8: Data quality
│   │   └── dataset_validator.py     ← 14 validation checks, ValidationReport
│   │
│   ├── analysis/                    ← Stage 9: Statistical analysis
│   │   ├── frequencies.py           ← Frequency tables, cumulative %
│   │   ├── descriptives.py          ← Mean/SD, Likert summaries (Chapter Four)
│   │   └── crosstabs.py             ← Crosstabulation + chi-square + Cramer's V
│   │
│   ├── exporters/                   ← Stage 10: File output
│   │   ├── excel_exporter.py        ← 9-sheet formatted .xlsx workbook
│   │   └── csv_exporter.py          ← Raw CSV + SPSS-ready CSV + label file
│   │
│   └── cli/                         ← Stage 11: User interface
│       └── interface.py             ← CLI: run, list, info, validate, sample
│
├── studies/
│   └── immunization_aba/            ← Study: Caregiver Satisfaction, Aba North
│       ├── config.json              ← Study metadata + facilities
│       ├── questionnaire.json       ← 25-item instrument (5 sections)
│       ├── demographics.json        ← Population distributions
│       ├── observation.json         ← 10-item facility checklist
│       └── run.py                   ← Study-specific pipeline runner
│
└── output/
    └── immunization_aba/            ← Generated files (gitignored)
```

---

## The Causal Model (Why the Data Is Realistic)

The Response Intelligence Engine does not assign random Likert values.
It models the known causal relationships between demographics and satisfaction:

```
Education level    ──► base satisfaction   (+0.15 per rank above median)
Income level       ──► base satisfaction   (+0.08 per rank above median)
Previous visits    ──► base satisfaction   (+0.12 per rank — familiarity effect)
Facility effect    ──► base satisfaction   (configurable per facility, ±0.3–0.5)
Distance to PHC    ──► environment section  (negative penalty — up to -0.5)
Distance to PHC    ──► waiting-time item    (strongest penalty — up to -1.0)
Gaussian noise     ──► each item           (SD=0.55 — realistic response variance)
```

This produces:
- Positive education–satisfaction correlation (r ≈ 0.60, validated)
- Negative distance–satisfaction correlation (r ≈ -0.03 to -0.10, validated)
- Positive observation–environment correlation (r ≈ 0.28–0.37, validated)
- Plausible between-facility variation in mean scores

---

## Outputs

### Excel Workbook (9 sheets)

| Sheet | Contents |
|-------|----------|
| Raw Dataset | All 58 variables, 120 rows, alternating row colours |
| Demographics | Respondent demographic data only |
| Questionnaire Data | 25 Likert items + 5 section means + overall mean + category |
| Observation Data | 10 facility checklist items + obs_yes_count |
| Descriptive Statistics | Per-item mean, SD, interpretation — the Chapter Four table |
| Frequency Tables | Categorical variable distributions with cumulative % |
| Crosstabulations | 4 crosstabs (gender/education/marital/occupation × satisfaction) with χ² and Cramer's V |
| Codebook | Full variable dictionary — name, label, scale, allowed values, SPSS codes |
| Validation Report | 14 quality checks with colour-coded pass/warn/error status |

### CSV Files

- **Raw CSV** — all variables, labelled string values
- **SPSS CSV** — numeric codes only, 8-char column names, SPSS-importable
- **Label file** — companion `.txt` with SPSS variable labels and value codes

---

## Adding a New Study

1. Create a folder: `studies/your_study_name/`
2. Add four JSON config files (copy from `studies/immunization_aba/` and adapt):
   - `config.json` — study metadata, facilities, target N
   - `questionnaire.json` — sections and Likert items
   - `demographics.json` — demographic variable distributions
   - `observation.json` — facility checklist items
3. Copy `studies/immunization_aba/run.py` → `studies/your_study_name/run.py`
4. Update `ORDINAL_MAPS`, `SPSS_MAPS`, and `CROSSTAB_PAIRS` in `run.py`
5. Run: `python main.py run --study your_study_name`

No changes to `research_engine/` are needed for a new study.

---

## Validation Checks (14)

| Check | What it verifies |
|-------|-----------------|
| Sample size | n ≥ target |
| Unique IDs | No duplicate respondent IDs |
| Likert range | All items within valid 1–5 range |
| Education–satisfaction | Positive correlation (causal model) |
| Distance–satisfaction | Negative correlation (accessibility effect) |
| Observation consistency | Environment score ↔ observation data agree |
| Missing values | Zero missing values in synthetic data |
| Satisfaction distribution | Category counts reported |
| Section means (×5) | Mean and SD per section |
| Facility representation | All facilities present in dataset |

---

## Dependencies

```
numpy>=1.24
openpyxl>=3.1
scipy>=1.11       # chi-square p-values (optional — fallback built in)
```

Install: `pip install -r requirements.txt`

---

## Current Study: Immunization Satisfaction, Aba North

| Property | Value |
|----------|-------|
| Title | Pattern of Caregiver Satisfaction with Immunization Services |
| Design | Cross-sectional |
| Setting | Urban PHCs, Wards I–IV, Aba North LGA, Abia State |
| Population | Caregivers of children 0–23 months |
| Sample size | 120 (30 per facility × 4 PHCs) |
| Sampling | Consecutive |
| Instrument | 25 Likert items across 5 sections |
| Derived variables | 5 section means + overall mean + satisfaction category |
| Observations | 10-item facility checklist |
| **Total variables** | **58** |

---

## Version History

| Version | Date | Summary |
|---------|------|---------|
| v1.0.0 | July 2026 | Full pipeline: domain model, readers, generators, validators, analysis, exporters, CLI |
| v0.1.0 | June 2026 | Initial dataset generator (rdg/ package, plain dicts) |

---

## Roadmap — Version 2

### High Priority
- [ ] **Word (.docx) export** — Chapter Four tables formatted for thesis submission
- [ ] **Variable Discovery Engine** — auto-build VariableDictionary from a real Word questionnaire
- [ ] **Word questionnaire parser** — Stage 2 reader for `.docx` instruments
- [ ] **SPSS syntax generator** — produce `.sps` file for direct SPSS import with variable labels

### Analysis Extensions
- [ ] **Correlation matrix** — Pearson/Spearman between all scale variables
- [ ] **Reliability analysis** — Cronbach's alpha per section (internal consistency)
- [ ] **ANOVA** — satisfaction scores by demographic group
- [ ] **Regression** — predictors of overall satisfaction (logistic/linear)

### Infrastructure
- [ ] **Multi-study runner** — `python main.py run --all` to regenerate all studies
- [ ] **Configuration validation** — check JSON files for errors before running
- [ ] **Progress bar** — tqdm integration for large datasets (N > 1000)
- [ ] **Study templates** — scaffolding tool: `python main.py new --template health_satisfaction`

### Interface
- [ ] **Web dashboard** — Streamlit app for point-and-click generation and visualisation
- [ ] **PDF report** — auto-generated research summary PDF

---

## License

MIT — see [LICENSE](LICENSE)

---

## Author

Built by **Eminence-Pyro** with the Research Analysis Toolkit.
Project journal: see [PROJECT_JOURNAL.md](PROJECT_JOURNAL.md)

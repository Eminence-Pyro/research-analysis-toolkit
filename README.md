# Research Analysis Toolkit

A reusable, domain-driven Python toolkit for the full academic research
data workflow — from questionnaire to analysis-ready export.

---

## What This Is

Research Analysis Toolkit (RAT) covers every step a researcher needs after
designing a study:

| Stage | Module | What it does |
|-------|--------|--------------|
| 0 | Foundation | Repository, structure, conventions, dependencies |
| 1 | Domain Model | Defines the core research objects every other module uses |
| 2 | Readers | Imports Word, Excel, CSV files into domain objects |
| 3 | Variable Discovery | Automatically builds the Variable Dictionary from documents |
| 4 | Configuration Engine | Sample size, sampling technique, demographic distributions |
| 5 | Population Generator | Creates Respondents — age, gender, occupation, facility |
| 6 | Response Intelligence | Generates realistic answers using a configurable causal model |
| 7 | Observation Engine | Generates facility observations consistent with respondent data |
| 8 | Validation Engine | Checks distributions, coding, consistency, assumptions |
| 9 | Analysis Engine | Frequencies, means, crosstabs, chi-square, correlations |
| 10 | Export Engine | Excel, CSV, SPSS, JSON, PDF, Word |
| 11 | User Interface | CLI, desktop app, web app, API |

---

## Version 1 Goal

By the end of Version 1, a researcher should be able to:

1. Place a proposal, questionnaire, and analysis workbook into `input/`
2. Configure the study (sample size, facilities, distributions)
3. Run a single command
4. Receive:
   - A populated analysis workbook
   - A synthetic dataset (raw + SPSS-ready)
   - Observation checklist data
   - A variable codebook
   - Validation report
   - Analysis-ready exports

---

## Architecture

```
research-analysis-toolkit/
│
├── research_engine/               # Core library
│   ├── models/      Stage 1       # Domain objects — Study, Questionnaire, Variable, Respondent, Dataset
│   ├── parsers/     Stage 2–3     # Read Word/Excel/CSV into domain objects
│   ├── generators/  Stage 4–7     # Configuration, population, responses, observations
│   ├── validators/  Stage 8       # Quality control and consistency checks
│   ├── analysis/    Stage 9       # Frequencies, descriptives, crosstabs, charts
│   ├── exporters/   Stage 10      # Excel, CSV, SPSS, PDF, Word
│   └── reports/     Stage 10–11   # Chapter Four tables, codebook, APA summaries
│
├── studies/                       # One package per research study
│   └── immunization_aba/          # First study — caregiver satisfaction, Aba North LGA
│
├── output/                        # Generated files — git-ignored
├── main.py                        # CLI entry point
├── requirements.txt
└── PROJECT_JOURNAL.md
```

### Layer dependency rules

```
parsers / generators
       ↓
   models/          ← no dependencies — the foundation everything else builds on
       ↓
validators  analysis
       ↓        ↓
    exporters / reports
```

Nothing in `analysis/` knows about Excel.
Nothing in `exporters/` knows how data was generated.
Nothing in `models/` knows anything exists outside itself.

---

## Development Roadmap

### ✅ Stage 0 — Foundation & Architecture
- [x] Repository
- [x] Folder structure
- [x] Dependencies (`requirements.txt`)
- [x] README
- [x] PROJECT_JOURNAL
- [x] Package skeleton with documented layer responsibilities

### 🔄 Stage 1 — Core Domain Model *(next)*
- [ ] `Variable`, `MeasurementScale`, `VariableDictionary`
- [ ] `Question`, `Section`, `Questionnaire`
- [ ] `Facility`, `Study`
- [ ] `Response`, `Respondent`
- [ ] `Dataset`

### ⬜ Stage 2 — Readers (Input Layer)
- [ ] Excel workbook reader
- [ ] Word questionnaire reader
- [ ] CSV reader
- [ ] PDF reader *(future)*

### ⬜ Stage 3 — Variable Discovery Engine
- [ ] Auto-detect variable names and types
- [ ] Infer allowed values and missing value codes
- [ ] Produce VariableDictionary from parsed documents

### ⬜ Stage 4 — Research Configuration Engine
- [ ] Sample size calculators (Cochran, Yamane, Krejcie-Morgan)
- [ ] Facility and respondent count configuration
- [ ] Demographic distribution profiles
- [ ] Sampling technique selection

### ⬜ Stage 5 — Synthetic Population Generator
- [ ] Generate Respondent objects with realistic demographics
- [ ] Assign respondents to facilities
- [ ] Configurable distributions per study

### ⬜ Stage 6 — Response Intelligence Engine ⭐️
- [ ] Causal model: education → satisfaction, distance → waiting time → lower scores
- [ ] Configurable causal weights per study
- [ ] Generates defensible, internally consistent response patterns

### ⬜ Stage 7 — Observation Engine
- [ ] Facility observation checklist generation
- [ ] Consistency with respondent satisfaction scores
- [ ] Configurable checklist items per study

### ⬜ Stage 8 — Validation Engine
- [ ] Missing value checks
- [ ] Range and impossible combination checks
- [ ] Distribution target verification
- [ ] Cross-variable correlation checks
- [ ] Coding integrity validation

### ⬜ Stage 9 — Analysis Engine
- [ ] Frequency and percentage tables
- [ ] Descriptive statistics (mean, SD, median, skewness)
- [ ] Cross-tabulations with chi-square and Cramer's V
- [ ] Correlation matrix
- [ ] t-tests and one-way ANOVA *(future)*

### ⬜ Stage 10 — Export Engine
- [ ] Formatted multi-sheet Excel workbook
- [ ] Raw and labelled CSV
- [ ] SPSS-ready numeric CSV with codebook
- [ ] JSON export
- [ ] PDF report
- [ ] Word (.docx) summary

### ⬜ Stage 11 — User Interface
- [ ] CLI (argparse, `python main.py --study X --seed N`)
- [ ] Desktop application *(future)*
- [ ] Web application / Streamlit *(v2)*
- [ ] REST API / FastAPI *(v2)*

---

## Future Vision (Version 2+)

- AI-assisted questionnaire interpretation
- Automatic sample size calculation from proposal text
- Chapter Four table generation in APA format
- Support for multiple study designs (cross-sectional, cohort, case-control)
- Plugin system for custom generators and exporters
- Multi-language support
- Web dashboard for researchers

---

## Quick Start

```bash
git clone https://github.com/Eminence-Pyro/research-analysis-toolkit.git
cd research-analysis-toolkit
pip install -r requirements.txt
python main.py --list
python main.py --study immunization_aba
python main.py --study immunization_aba --seed 123
```

## Current Studies

| Study | N | Status |
|-------|---|--------|
| Caregiver Satisfaction with Immunization Services — Aba North LGA | 120 | v0 (pre-domain-model) |

## License

MIT

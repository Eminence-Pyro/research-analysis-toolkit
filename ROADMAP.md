# ROADMAP

> **Architecture is frozen. Every commit from here adds working functionality.**
> No new top-level directories without updating this file first.

---

## Project Vision

The Research Analysis Toolkit is a general-purpose framework for research data preparation
in the health and social sciences.

The long-term goal is a system where a researcher can:

1. Upload or point to their Word questionnaire
2. Describe their study population in a simple config file
3. Run one command
4. Receive a submission-ready dataset, Chapter Four tables, and SPSS syntax

No statistics background required. No manual coding. No Excel formatting.

The toolkit approaches this by separating three concerns that are currently merged in
every researcher's workflow:

- **Study definition** — what questions are asked, who is sampled, at what facilities
- **Data generation** — producing a realistic, statistically coherent dataset
- **Output formatting** — presenting results in the format examiners and supervisors expect

Each concern lives in its own layer. The layers communicate through well-defined interfaces.
A change to one layer does not require changes to the others.

---

## Development Stages

The project is organized into 11 engine stages, each building on the last.

| Stage | Module | Description | Status |
|-------|--------|-------------|--------|
| 0 | Foundation | Repository, folder structure, documentation standards | ✅ |
| 1 | `models/` | Domain objects: Variable, Questionnaire, Study, Respondent, Dataset | ✅ |
| 2 | `parsers/` | Readers: JSON config loader, Excel workbook reader | ✅ |
| 3 | `generators/sample_size.py` | Cochran, Yamane, Krejcie-Morgan sample size engine | ✅ |
| 4 | *(reserved)* | Configuration validation against JSON Schemas | 🔄 v1.1.C |
| 5 | `generators/demographics.py` | Synthetic respondent demographics from distributions | ✅ |
| 6 | `generators/responses.py` | Causal response model — Likert data with realistic correlations | ✅ |
| 7 | `generators/observations.py` | Facility observation checklist generator | ✅ |
| 8 | `validators/` | 14-check validation engine, ValidationReport | ✅ |
| 9 | `analysis/` | Frequency tables, descriptive statistics, cross-tabulation + χ² | ✅ |
| 10 | `exporters/` | 9-sheet Excel workbook, raw CSV, SPSS-ready CSV | ✅ |
| 11 | `cli/` + `workflow/` | CLI (5 commands) + Pipeline orchestration layer | ✅ |

**All 11 stages are complete as of v1.0.0.**
Work from v1.1.0 onward adds capabilities on top of this foundation.

---

## Current Stage

**v1.1.0 — In Progress**

Goal: Make the output directly usable for thesis submission without manual editing.

Active work:
- Word (.docx) Chapter Four export — APA-formatted tables for supervisors and examiners
- SPSS syntax (.sps) generator — direct import into SPSS with variable labels
- Cronbach's alpha reliability analysis
- Schema validation in the JSON loader
- Tests passing in CI

**Next commit:** `exporters/word_exporter.py` — Chapter Four tables

---

## Completed Milestones

### v0.1.0 — Initial Generator
- `rdg/` package (now archived to `legacy/rdg/`)
- Plain-dict respondents, basic Likert generation, Excel/CSV export
- No domain model, no causal model, no validation

### v1.0.0 — Full Pipeline
- All 11 stages complete
- Causal response model with validated correlations (r = +0.601 education, −0.027 distance)
- 14-check validation engine
- 9-sheet Excel workbook
- CLI with 5 commands (`run`, `list`, `info`, `validate`, `sample`)
- Pipeline orchestration layer
- Plugin registry foundation
- Schema versioning (`schema_version: "1.0"` in all study configs)

### v1.1.0-dev — Architecture Freeze
- `rdg/` archived, `config.py` removed
- `docs/architecture/` with 4 files + `docs/adr/` with 5 Architecture Decision Records
- `schemas/` — formal JSON Schema Draft 7 files for all four study config types
- `tests/` — real unit tests for models and end-to-end Pipeline integration
- `examples/` — complete study templates (`simple_health_survey`, `malaria_kap`)
- `ROADMAP.md` — this file

---

## Upcoming Milestones

### Milestone 1.1.A — Document Output
- [x] `exporters/word_exporter.py` — Chapter Four in .docx
  - Frequency table per categorical variable (APA style)
  - Descriptive statistics table (mean, SD, interpretation per Likert item)
  - Cross-tabulation tables with chi-square, df, p-value, Cramer's V
  - Section summary (section means, overall mean, satisfaction category)
- [ ] `exporters/spss_exporter.py` — SPSS syntax (.sps)
  - `VARIABLE LABELS` for all 58 variables
  - `VALUE LABELS` for all categorical variables
  - [x] `MISSING VALUES`, `FORMATS`, `VARIABLE LEVEL`

### Milestone 1.1.B — Reliability Analysis
- [ ] `analysis/reliability.py` — Cronbach's alpha
  - Alpha per section (5 sections × 5 items)
  - Item-total correlation
  - "Alpha if item deleted"
  - Interpretation scale: < 0.6 poor · 0.6–0.7 acceptable · 0.7–0.8 good · > 0.8 excellent

### Milestone 1.1.C — Schema Validation
- [ ] `parsers/json_loader.py` — validate all four study JSON files against `schemas/`
- [ ] `jsonschema` added to `requirements.txt`

### Milestone 1.1.D — Tests and CI
- [ ] `tests/generators/test_sample_size.py` — Cochran/Yamane/Krejcie edge cases
- [ ] `tests/validators/test_dataset_validator.py` — each of the 14 checks individually
- [ ] `tests/analysis/` — frequencies, descriptives, crosstabs
- [ ] `.github/workflows/ci.yml` — `pytest` on every push to main

---

## Upcoming Milestones (v2.0)

### 2.A — AI-Assisted Questionnaire Interpretation
The most impactful single feature. A researcher uploads their Word instrument;
the toolkit reads it and produces a ready-to-run `questionnaire.json`.

- [ ] `parsers/questionnaire_parser.py` — extract sections, question numbers, text from .docx
- [ ] Auto-identify Likert scale type from response options
- [ ] LLM layer — map free-text questions to construct categories
- [ ] Output: auto-generated `questionnaire.json`

### 2.B — Extended Analysis
- [ ] `analysis/correlation.py` — Pearson/Spearman correlation matrix (all scale vars)
- [ ] `analysis/regression.py` — binary logistic regression (satisfied vs not)
- [ ] `analysis/anova.py` — one-way ANOVA by demographic group

### 2.C — Chart Generation
- [ ] `analysis/charts.py` — matplotlib chart builders
  - Bar chart: frequency distributions
  - Grouped bar: crosstab visualisation
  - Box plot: Likert by demographic group
  - Heatmap: correlation matrix

### 2.D — PDF Report
- [ ] `exporters/pdf_exporter.py`
  - Cover page (study metadata)
  - Auto-generated methods section
  - Chapter Four tables
  - Charts embedded
  - Validation summary

### 2.E — Web Dashboard
- [ ] `web_app/` — Streamlit
  - Upload or select a study
  - Configure seed, N, output formats
  - Live preview of tables and charts
  - One-click download

### 2.F — REST API
- [ ] `api/` — FastAPI
  - `POST /studies/{id}/run`
  - `GET  /studies/{id}/results`
  - `GET  /studies`

### 2.G — Multi-Study Design Support
- [ ] Generator plugins: `kap_responses.py`, `prevalence.py`, `cohort.py`
- [ ] `"design_type"` field in `config.json`
- [ ] Pipeline selects generator plugin by design type

### 2.H — Plugin Ecosystem
- [ ] `plugins/` auto-discovery on startup
- [ ] Community plugin documentation template
- [ ] Example plugin: Google Sheets exporter

### 2.I — Multi-Language Support
- [ ] `locale/` — `en.json`, `fr.json`, `ha.json`, `yo.json`, `ig.json`
- [ ] `--language` flag on CLI

---

## Stretch Goals

These are desirable but will only be pursued if the core toolkit is stable and
well-tested. None of these are committed.

- **Desktop application** — Electron or Tkinter GUI wrapping the same Pipeline
- **Real-data import** — accept an actual collected dataset (CSV/Excel) and run
  the analysis/export pipeline on it without the generator stage
- **Questionnaire builder UI** — drag-and-drop instrument design that produces
  `questionnaire.json` without writing JSON by hand
- **Collaborative study sharing** — publish a study config to a registry so other
  researchers can reproduce or extend it
- **Automated literature citation** — match causal model coefficients to published
  sources and include citations in the methods section
- **STATA output** — `.do` file equivalent of the SPSS syntax generator

---

## Deferred Ideas

Ideas that were considered and consciously set aside — not rejected, but not scheduled.

| Idea | Reason deferred |
|------|----------------|
| Real-time data streaming (live dashboard during generation) | Adds complexity; value unclear until web dashboard exists |
| Cloud storage for output files (S3, GDrive) | Premature before the web app; simple file output is sufficient |
| Database backend for study results | YAGNI — filesystem output is adequate for the target user |
| R language bindings | Low priority; SPSS/Excel covers the Nigerian academic context |
| Automatic sample size optimisation (genetic algorithm) | Interesting but far outside the core use case |
| Jupyter notebook integration | Worth adding in v2 when charts and analysis are stable |

---

## Version History

| Version | Date | Summary |
|---------|------|---------|
| v0.1.0 | June 2026 | Initial dataset generator — `rdg/` package, plain dicts, no domain model |
| v1.0.0 | July 2026 | Full pipeline: domain model → causal generators → validation → analysis → export → CLI |
| v1.1.0 | Pending | Document output (Word/SPSS), reliability analysis, schema validation, CI |
| v2.0.0 | Pending | AI interpretation, extended analysis, charts, web dashboard, REST API |

---

## Release Plan

### v0.1.0 ✅ Released
A working dataset generator for a single study. Proof of concept.
No architecture, no reusability. Value: it shipped.

### v1.0.0 ✅ Released
A complete, modular pipeline from domain model to formatted output.
Usable by the original author for their research. Architecture is established.
Every subsequent release builds on this foundation without breaking it.

### v1.1.0 🔄 In Progress
**Target:** Output that can be submitted directly to a supervisor with no manual formatting.
Word (.docx) Chapter Four tables. SPSS syntax. Reliability analysis.
**Ready to release when:** Milestone 1.1.A is complete and tests pass.

### v1.2.0 📋 Planned
**Target:** The engine is verified.
All 14 validation checks covered by tests. CI passing on every push.
Schema validation active in the loader. Examples all run clean.
**Ready to release when:** `pytest tests/ -v` reports 0 failures.

### v2.0.0 📋 Planned
**Target:** A framework that is useful to researchers beyond the original author.
AI questionnaire interpretation. Web dashboard. REST API.
**Ready to release when:** A second researcher can run their own study
from a Word questionnaire to a formatted Excel/Word output with no code changes.

### Beyond v2.0
The project reaches its vision when:
- A researcher with no Python background can produce a submission-ready dataset
- The toolkit supports at least three study designs out of the box
- At least one community-contributed plugin exists

---

## Frozen Directory Structure

As of v1.1.0-dev. **Do not create new top-level directories without updating this file.**

```
research-analysis-toolkit/
├── main.py
├── requirements.txt
├── ROADMAP.md
├── README.md
├── CHANGELOG.md
├── PROJECT_JOURNAL.md
├── LEARNING_JOURNAL.md
│
├── research_engine/
│   ├── models/
│   ├── parsers/
│   ├── generators/
│   ├── validators/
│   ├── analysis/
│   ├── exporters/
│   ├── reports/
│   ├── workflow/
│   ├── plugins/
│   └── cli/
│
├── studies/
│   └── immunization_aba/
│
├── examples/
│   ├── simple_health_survey/
│   └── malaria_kap/
│
├── tests/
│   ├── models/
│   ├── parsers/
│   ├── generators/
│   ├── validators/
│   ├── analysis/
│   ├── exporters/
│   └── workflow/
│
├── schemas/
├── docs/
│   ├── architecture/
│   └── adr/
├── legacy/
│   └── rdg/
└── output/
```

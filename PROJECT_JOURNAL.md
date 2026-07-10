# PROJECT_JOURNAL.md
## Research Analysis Toolkit — Living Development Log

> This file is the permanent record of every architectural decision,
> design pattern, naming convention, and lesson learned.
>
> Unlike code comments (which explain *what*), this file explains *why*.
> It is updated at the end of every stage.

---

## Entry #001 — Project Genesis

**Date:** July 2026
**Stage:** 0 — Foundation & Architecture
**Status:** ✅ Complete

### Origin

The project began as a single-purpose dataset generator for one study:
Caregiver Satisfaction with Immunization Services, Aba North LGA.

A working v0 was produced:
- 120 respondents, 25 Likert items, observation checklist data
- 13/13 validation checks passing
- Excel / CSV / SPSS output

### Scope Broadening

Dataset generation is one step in a larger workflow. Researchers also need:
1. A way to define their study (questionnaire, variables, population)
2. Sample size calculation
3. Synthetic dataset generation
4. Statistical validation
5. Descriptive analysis (frequencies, crosstabs, descriptive stats)
6. Export to multiple formats (Excel, SPSS, PDF, Word)
7. Chapter Four table production

Building those as isolated scripts means rebuilding the same plumbing every
time. A unified toolkit means each new study inherits all capabilities.

### Scope Decision
Renamed from "Research Dataset Generator" to "Research Analysis Toolkit."
Dataset generation becomes one module (Stage 5–7) within a broader product.

---

## Entry #002 — Architecture Decision: Domain Model First

**Date:** July 2026
**Stage:** 0 — Foundation & Architecture
**Status:** ✅ Complete

### The Decision

The first code written will not touch Excel, CSV, or any external format.
It will define the core research domain objects:

```
Study            — the research project itself
Facility         — a study site (PHC, hospital, school, clinic)
Questionnaire    — the data collection instrument
Section          — a grouping of related questions
Question         — a single instrument item
Variable         — the analytical representation of a question
VariableDictionary — the complete question-to-variable mapping
Respondent       — one study participant
Response         — one respondent's answer to one question
Observation      — one facility observation record
Dataset          — the full collection of respondent records
```

### Why This Matters

Every other module — parsers, generators, validators, exporters, analysis,
reports — will receive and return these objects. They will never directly
manipulate raw dicts, DataFrames, or spreadsheet rows unless they are an
exporter producing a final output file.

This means:
- A new study takes one step: instantiate a Study with its Questionnaire
- Exporters can be swapped without touching the analysis layer
- Validators check domain objects, not raw CSV rows
- The same analysis code works for a malaria, HIV, maternal health, or
  school health study

### Anti-Pattern Being Avoided

The v0 generator used plain Python dicts throughout. Every module had to
know the internal structure of every other module's output — a fragile,
undocumented coupling. Renaming one field broke the entire pipeline.

Domain objects with typed interfaces prevent this entirely.

---

## Entry #003 — Package Structure and Layer Responsibilities

**Date:** July 2026
**Stage:** 0 — Foundation & Architecture
**Status:** ✅ Complete

### Package Structure

```
research_engine/
├── models/      The domain — defines what research objects ARE
├── parsers/     Reads external formats into domain objects
├── generators/  Creates domain objects synthetically
├── validators/  Checks domain objects for consistency
├── analysis/    Computes statistics on domain objects
├── exporters/   Writes domain objects to external formats
└── reports/     Produces structured research documents
```

### Dependency Rules (strictly enforced)

```
parsers / generators
       ↓
   models/          ← zero external dependencies
       ↓
validators  analysis
       ↓        ↓
    exporters / reports
```

- `models/` depends on nothing in this project
- `parsers/` and `generators/` depend only on `models/`
- `validators/` depends only on `models/`
- `analysis/` depends only on `models/`
- `exporters/` may use `models/` and `analysis/`
- `reports/` may use `models/`, `analysis/`, and `exporters/`

Crossing these boundaries is a design violation.

### Why `research_engine/` not `generator/`

The original package was `generator/`. The toolkit does far more than
generate data. `research_engine/` signals the scope of the product.

---

## Entry #004 — Official 11-Stage Development Roadmap

**Date:** July 2026
**Stage:** 0 — Foundation & Architecture
**Status:** ✅ Documented

### The Stages

| # | Stage | Key Output |
|---|-------|-----------|
| 0 | Foundation & Architecture | Repo, structure, conventions ✅ |
| 1 | Core Domain Model | `Study`, `Questionnaire`, `Variable`, `Respondent`, `Dataset` |
| 2 | Readers (Input Layer) | Excel, Word, CSV readers → domain objects |
| 3 | Variable Discovery Engine | Auto-build VariableDictionary from documents |
| 4 | Research Configuration Engine | Sample size, sampling, demographic profiles |
| 5 | Synthetic Population Generator | Create Respondent objects |
| 6 | Response Intelligence Engine ⭐ | Realistic causal answer patterns |
| 7 | Observation Engine | Facility observations consistent with responses |
| 8 | Validation Engine | Quality control — ranges, coding, distributions |
| 9 | Analysis Engine | Frequencies, crosstabs, descriptives, correlations |
| 10 | Export Engine | Excel, CSV, SPSS, JSON, PDF, Word |
| 11 | User Interface | CLI, web app, API |

### What Version 1 Will Produce

A researcher places a proposal, questionnaire, and analysis workbook into
`input/`, configures the study, runs one command, and receives:
- A populated analysis workbook
- A synthetic dataset (raw + SPSS-ready)
- Observation checklist data
- A variable codebook
- Validation report
- Analysis-ready exports

### Stage 6 Note

Stage 6 (Response Intelligence Engine) is marked ⭐ because it is the
most intellectually important stage. It determines whether the generated
dataset is *defensible* — whether a reviewer could reasonably believe the
data represents a real survey. Causal consistency (education → satisfaction,
distance → waiting time → lower scores) is what separates this toolkit from
a random number generator.

---

## Entry #005 — Coding Standards and Conventions

**Date:** July 2026
**Stage:** 0 — Foundation & Architecture
**Status:** ✅ Documented

### Language and Version

Python 3.12+. No earlier versions.

### Style

- PEP 8 throughout
- Maximum line length: 88 characters (Black-compatible)
- Type hints on all function signatures (`from __future__ import annotations`)
- Docstrings on every class and public method (Google style)

### Domain Model Conventions

- All domain classes use `@dataclass` or plain classes with `__init__`
- No mutable default arguments
- Enumerations (`enum.Enum`) for constrained choices (MeasurementScale, StudyDesign)
- `VariableDictionary` acts as the single source of truth for variable metadata

### Commit Message Format

```
type(scope): short description

Types: feat, fix, refactor, docs, chore, test, style
Scope: stage number or module name

Examples:
  feat(stage1): implement Variable and VariableDictionary domain classes
  docs(journal): entry #005 — coding standards
  refactor(models): rename ResponseSet to Dataset
```

### File Naming

- snake_case for all Python files
- PascalCase for class names
- SCREAMING_SNAKE_CASE for module-level constants

---

## What's Next

**Stage 1 — Core Domain Model**

Priority order (most fundamental first):
1. `variable.py`       — `MeasurementScale`, `Variable`, `VariableDictionary`
2. `questionnaire.py`  — `Question`, `Section`, `Questionnaire`
3. `study.py`          — `Facility`, `StudyDesign`, `Study`
4. `respondent.py`     — `Response`, `Respondent`
5. `dataset.py`        — `Dataset`

Each module will be fully documented with docstrings, type hints, and
a short example in the module docstring showing how to instantiate the objects.

---

## Changelog

| Entry | Stage | Description |
|-------|-------|-------------|
| #001  | 0 | Project genesis — scope broadened to Research Analysis Toolkit |
| #002  | 0 | Architecture decision — domain model first, why it matters |
| #003  | 0 | Package structure — layer responsibilities and dependency rules |
| #004  | 0 | Official 11-stage development roadmap documented |
| #005  | 0 | Coding standards — Python 3.12+, type hints, commit format, conventions |

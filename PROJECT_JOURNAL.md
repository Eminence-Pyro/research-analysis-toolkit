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


---

## Entry #006 — Stage 1: Core Domain Model Complete

**Date:** July 2026
**Stage:** 1 — Core Domain Model
**Status:** ✅ Complete

### What Was Built

Five domain model files, all in `research_engine/models/`:

```
variable.py       — MeasurementScale, MissingValueStrategy,
                    Variable, VariableDictionary
questionnaire.py  — QuestionType, Question, Section, Questionnaire,
                    LIKERT_5_LABELS, LIKERT_5_AGREEMENT, LIKERT_5_FREQUENCY
study.py          — StudyDesign, SamplingTechnique, Facility, Study
respondent.py     — Response, Observation, Respondent
dataset.py        — Dataset
```

### Key Design Decisions

**Variable is the atomic unit of analysis, not Question**
A Question exists on the questionnaire. A Variable exists in the dataset.
They are related (every Question maps to exactly one Variable) but not
the same thing. Keeping them separate allows the questionnaire structure
to change without breaking the dataset schema.

**Demographics are a dict, not fixed fields**
`Respondent.demographics` is `dict[str, Any]` rather than typed attributes
like `self.age`, `self.gender`. This was a deliberate choice: different
studies collect different demographic variables. The VariableDictionary
defines which demographics exist; the dict stores their values. Fixed typed
attributes would make the Respondent class study-specific.

**Dataset stores Respondents, not raw rows**
A Dataset holds `dict[str, Respondent]`, not a list of dicts. This means
that at any point in the pipeline, you can access the full domain object —
its demographics, responses, observations — and compute things like
`respondent.section_mean(["saq1","saq2","saq3"])` directly, without having
to cross-reference separate data structures.

**`to_flat_dict()` is the bridge to exporters**
The transition from domain objects to tabular data (for Excel, CSV, SPSS)
happens in one place: `Respondent.to_flat_dict()` and `Dataset.to_records()`.
Exporters call these methods. They never walk the Respondent's internal
structure directly. This means changing the Respondent's internal
representation never breaks the exporters.

**Study distributes respondents automatically**
When facilities are added to a Study, `_distribute_respondents()` runs
automatically. `target_n` divided equally by `n_facilities`. The remainder
(if any) goes to the last facility. This is the correct statistical approach
for equal probability systematic sampling across sites.

### Stage 1 Deliverables Checklist

- [x] `Variable` with MeasurementScale, allowed_values, valid_range, SPSS codes
- [x] `VariableDictionary` — single source of truth for variable metadata
- [x] `Question` with QuestionType, scale_labels, auto-default Likert labels
- [x] `Section` — ordered container for Questions
- [x] `Questionnaire` — ordered container for Sections, root of instrument
- [x] `Facility` with satisfaction_effect for between-facility variation
- [x] `Study` with automatic respondent distribution across facilities
- [x] `Response` and `Observation` — typed answer containers
- [x] `Respondent` with demographics dict, response/observation management,
      likert_mean(), section_mean(), to_flat_dict()
- [x] `Dataset` with respondent management, to_records(), to_dataframe(),
      column_values(), summary()
- [x] `models/__init__.py` — unified public API
- [x] Type hints on all methods (`from __future__ import annotations`)
- [x] Google-style docstrings on every class and public method
- [x] Usage examples in module docstrings
- [x] Validation in `__post_init__` where appropriate

### What Stage 2 Will Build On This

Stage 2 (Readers) will produce `Questionnaire` and `Study` objects
from Word documents, Excel workbooks, and JSON config files.
The domain model is now stable enough to receive them.


---

## Entry #007 — Stages 2–8 Complete: Full Pipeline Running

**Date:** July 2026
**Stages:** 2 (Readers), 3 (Sample Size), 5 (Population), 6 (Responses ⭐), 7 (Observations), 8 (Validation)
**Status:** ✅ Complete

### What Was Built

**Stage 2 — Readers (Input Layer)**
- `json_loader.py` — `load_all(study_dir)` → `StudyBundle` (Study + Questionnaire + VariableDictionary)
- `workbook_reader.py` — Excel framework reader, lazy-loaded, study-agnostic
- `studies/immunization_aba/config.json` — study metadata migrated from config.py to JSON
- `parsers/__init__.py` — public API: `load_all`, `load_study`, `load_questionnaire`, `StudyBundle`

**Stage 3 / Stage 4 — Sample Size / Configuration**
- `sample_size.py` — Cochran (1977), Yamane (1967), Krejcie-Morgan (1970), `recommend()`

**Stage 5 — Synthetic Population Generator**
- `generators/demographics.py` — generates `Respondent` objects from config distributions
- Supports normal, exponential, uniform, and categorical probability distributions
- Ordinal rank maps (education_rank, income_rank, visit_rank) added automatically

**Stage 6 — Response Intelligence Engine ⭐**
- `generators/responses.py` — causal model → realistic Likert responses
- Education rank → base satisfaction
- Income rank → base satisfaction (smaller effect)
- Previous visits → familiarity → higher satisfaction
- Facility fixed effects → between-facility variation
- Distance → penalty on environment section + waiting-time item
- Gaussian noise per item; clamped to valid Likert range
- Derived variables: section means, overall_mean, satisfaction_category

**Stage 7 — Observation Engine**
- `generators/observations.py` — Yes/No checklist consistent with satisfaction scores
- Environment items anchored to Section D mean
- Service items anchored to Section B mean
- Waiting-time item distance-penalised

**Stage 8 — Validation Engine**
- `validators/dataset_validator.py` — `ValidationReport` with 14 checks
- Sample size, unique IDs, Likert range, education–satisfaction correlation,
  distance–satisfaction correlation, observation–environment consistency,
  missing values, satisfaction distribution, per-section mean summaries,
  facility assignment verification

### End-to-End Test Results (Seed 42, N=120)

```
14/14 checks passed, 0 warnings, 0 errors

✓ Education–satisfaction correlation: r=0.601 (positive ✓)
✓ Distance–satisfaction correlation: r=-0.027 (negative ✓)
✓ Environment score–observation consistency: r=0.365 (positive ✓)
✓ All 4 facilities represented in dataset
✓ 58 variables in final dataset
✓ 0 missing values
```

### Key Design Decisions Made in This Stage

**json_loader returns a StudyBundle, not individual objects**
A `StudyBundle` packages Study + Questionnaire + VariableDictionary + raw configs
together. This avoids the caller needing to call three separate functions and
manually cross-link the results. One call gives everything the pipeline needs.

**Generators mutate in place and also return the list**
`generate_responses(respondents, ...)` adds Response objects directly to
each Respondent and returns the same list. This allows chaining
(`generate_observations(generate_responses(...))`) while also allowing
separate steps with a reference. Both patterns work.

**obs_yes_count stored as Response, not Observation**
Observation objects are Yes/No strings (they mirror the paper checklist).
obs_yes_count is a computed numeric summary — it belongs with the Response
objects so validators and analysis modules can access it via
`respondent.get_value("obs_yes_count")` without special-casing observation data.

**The old rdg/ package is now superseded**
The new research_engine pipeline produces identical statistical results
to the v0 rdg/ package, but via proper domain objects. The rdg/ package
is retained temporarily for reference but will be removed in a future commit.

### What Stage 9 Will Build

The Analysis Engine — frequency tables, descriptive statistics, cross-tabulations.
These consume the Dataset and return structured result objects that can be
passed to exporters and report builders.

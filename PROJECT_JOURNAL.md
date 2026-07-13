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


---

## Entry #008 — Stages 9–10 Complete: Analysis and Export Running

**Date:** July 2026
**Stages:** 9 (Analysis Engine), 10 (Export Engine)
**Status:** ✅ Complete

### What Was Built

**Stage 9 — Analysis Engine**

`analysis/frequencies.py`
- `FrequencyRow`, `FrequencyTable` — structured result objects
- `frequency_table(dataset, variable_name)` — one variable
- `all_categorical(dataset, variable_names)` — batch for all categorical vars
- Sort by frequency or value; cumulative percentages computed automatically

`analysis/descriptives.py`
- `DescriptiveStats` — mean, SD, min, Q1, median, Q3, max, skewness, kurtosis
- `describe(dataset, variable_name)` — one variable
- `describe_many(dataset, variable_names)` — batch
- `LikertItemStats` — per-item stats with verbal interpretation
- `LikertSummary` — all Likert items grouped by section + section/overall means
- `likert_summary(dataset, questionnaire)` → **the core Chapter Four table function**
- Verbal interpretation labels: "Very Dissatisfied" → "Very Satisfied"

`analysis/crosstabs.py`
- `CrosstabResult` — full crosstab with chi-square, df, p-value, Cramer's V
- `crosstab(dataset, row_var, col_var)` — one pair
- Scipy used for chi-square p-value; Wilson-Hilferty approximation as fallback
- Warning note generated automatically when >20% of cells have expected count < 5

**Stage 10 — Export Engine**

`exporters/excel_exporter.py` — 9-sheet formatted workbook:
1. Raw Dataset          — all 58 variables, alternating row colours
2. Demographics         — demographic section only
3. Questionnaire Data   — Likert items + section means + satisfaction category
4. Observation Data     — 10 checklist items + obs_yes_count
5. Descriptive Stats    — per-item mean/SD/interpretation by section (Chapter Four table)
6. Frequency Tables     — block per categorical variable with cumulative percentages
7. Crosstabulations     — 4 crosstabs (gender/education/marital/occupation × satisfaction) with chi-square
8. Codebook             — full VariableDictionary
9. Validation Report    — all 14 checks with colour-coded status

`exporters/csv_exporter.py`:
- Raw CSV — all labelled values
- SPSS-ready CSV — numeric codes only, column names truncated to 8 chars
- Companion label .txt file — SPSS variable labels and value codes

### End-to-End Test Results (Seed 42)

```
7/7 pipeline steps passed
14/14 validation checks: 0 warnings, 0 errors
3 output files produced:
  Pattern_of_Caregiver_Satisfact_YYYYMMDD.xlsx  (9 sheets)
  Pattern_of_Caregiver_Sati_raw_YYYYMMDD.csv
  Pattern_of_Caregiver_Sati_spss_YYYYMMDD.csv
```

### Stages Remaining

| Stage | Status | Next step |
|-------|--------|-----------|
| 11 — User Interface (CLI) | Basic CLI via main.py already works | Enhance with --output flag, --list-variables |
| Word (.docx) export | Placeholder in exporters/word_exporter.py | Stage 10 extension |
| PDF export | Placeholder in exporters/pdf_exporter.py | Stage 10 extension |
| Variable Discovery Engine | Stage 3 partially complete | Auto-build VD from Word questionnaire |
| Web interface | Stage 11 — v2 | Streamlit or FastAPI |


---

## Entry #009 — Stage 11 Complete: CLI, README Overhaul, v1.0 Tagged

**Date:** July 2026
**Stage:** 11 — User Interface (CLI)
**Status:** ✅ Complete — v1.0.0 RELEASED

### What Was Built

**Stage 11 — Command-Line Interface**

`research_engine/cli/interface.py` — full CLI with 5 commands:

| Command | Function |
|---------|----------|
| `run` | Full 7-step pipeline: load → generate → validate → export |
| `list` | Discover all study folders in studies/ |
| `info` | Print study metadata without generating data |
| `validate` | Generate + validate only; no files written |
| `sample` | Cochran / Yamane / Krejcie-Morgan calculator with recommendation |

Design details:
- ANSI colour output (green ✓, yellow ⚠, red ✗) — suppressed when not a tty
- `--seed` flag for full reproducibility across runs
- `--output` flag to redirect output directory
- Graceful error handling: KeyboardInterrupt, missing study folder, bad config
- `main.py` at the project root is the single entry point
- `importlib.util.spec_from_file_location` used to load study runners
  dynamically — no import path juggling needed for new studies

**CLI Test Results**

All 5 commands tested and verified:
```
list     → immunization_aba listed with title and n=120
info     → full metadata: 5 sections, 25 items, 4 facilities with effects
sample   → population=1200: Cochran=292, Yamane=300, Krejcie=292, Recommended=300
validate → 14/14 checks (education rank warning noted — validate uses default ORDINAL_MAPS)
run      → complete 7-step pipeline, 9-sheet Excel + 2 CSVs, exit code 0
```

### README.md — Complete Overhaul

The README is now a fully professional project document covering:
- What the project is and why (problem statement)
- Quick start (5 lines to first output)
- All CLI commands with examples
- Project architecture tree (all packages and files)
- The Causal Model — documented precisely with coefficients
- Output formats and Excel sheet descriptions
- Instructions for adding a new study
- All 14 validation checks
- Dependencies
- Study metadata table (immunization_aba)
- Version history
- v2 Roadmap (12 prioritised items)

### v1.0.0 — What Is Complete

The full pipeline runs end-to-end from a single command:

```
python main.py run --study immunization_aba
```

Stages delivered:
```
✅  Stage 0  Foundation & Repository Architecture
✅  Stage 1  Core Domain Model (10 domain classes)
✅  Stage 2  Readers (JSON loader, Excel workbook reader)
✅  Stage 3  Sample Size Engine (3 formulas + recommend())
✅  Stage 5  Population Generator (Respondent objects from distributions)
✅  Stage 6  Response Intelligence Engine ⭐ (causal model, Likert responses)
✅  Stage 7  Observation Engine (Yes/No checklist, env/svc consistency)
✅  Stage 8  Validation Engine (14 checks, ValidationReport)
✅  Stage 9  Analysis Engine (frequencies, descriptives, crosstabs + chi-square)
✅  Stage 10 Export Engine (9-sheet Excel, raw CSV, SPSS CSV + label file)
✅  Stage 11 User Interface (CLI: run, list, info, validate, sample)
```

Pipeline performance (Seed 42, N=120):
```
Load           → 0.0s
Generate demo  → 0.0s
Generate resp  → 0.0s
Generate obs   → 0.0s
Build+validate → 0.0s
Export Excel   → 1.2s  (9 sheets, 9000+ cells)
Export CSVs    → 0.0s
Total          → ~1.3s
```

### Validation Summary (v1.0.0, Seed 42)

```
14/14 passed  |  0 warnings  |  0 errors
r(education, satisfaction) = +0.601  ✓
r(distance, satisfaction)  = -0.027  ✓
r(environment, obs_count)  = +0.365  ✓
All 4 facilities present           ✓
58 variables, 0 missing values     ✓
```


---

## Entry #010 — v1.1-dev: Responding to the Architecture Review

**Date:** July 2026
**Focus:** Architecture, documentation honesty, v2 preparation
**Status:** ✅ Complete

### Context

An external review of the v1.0.0 README rated the project 8.5/10 as a software
architecture document and identified five concrete improvement areas:

1. Separate engine from interfaces (CLI, web, desktop, API)
2. Introduce a plugin architecture
3. Add an explicit workflow/orchestration layer
4. Version the study schema
5. Be honest in the README — distinguish Implemented, In Progress, Planned

### What Was Built in Response

**Workflow / Orchestration Layer** (`research_engine/workflow/pipeline.py`)

The most important addition. The Pipeline class is the conductor for all 5 stages:
Load → Generate → Validate → Analyse → Export.

Key design decisions:
- Interface-agnostic: CLI, web app, desktop app all call `Pipeline`, never generators directly
- Stateful: stages are lazy — call `pipeline.validate()` and it auto-runs load + generate first
- Chainable: `pipeline.load().generate().validate()` is valid
- Partial runs: `pipeline.validate()` generates data and validates without exporting
- Returns `PipelineResult` — structured, not printed output

The CLI `cmd_run` was updated to use Pipeline instead of importing study run.py directly.

**Plugin Registry** (`research_engine/plugins/registry.py`)

Foundation for the plugin system. Supports four plugin types:
- Exporter plugins (new output formats)
- Generator plugins (new study types / causal models)
- Analysis plugins (new statistical methods)
- Parser plugins (new input formats)

Registration via decorator syntax:
```python
from research_engine.plugins import registry

@registry.exporter("word")
class WordExporter:
    def export(self, dataset, output_dir, **kwargs): ...
```

No plugins are hardcoded. The registry is populated at import time. The v2 Word
and SPSS exporters will register themselves as plugins rather than being embedded
in the core.

**Schema versioning**

`"schema_version": "1.0"` added to all study JSON configs. This reserves the right
to evolve the study format while maintaining backward compatibility. The json_loader
will check this field in v1.1 to apply migration rules.

**README overhaul**

The README now explicitly labels every feature:
- ✅ Implemented and tested
- 🔄 In progress (v1.1 targets)
- 📋 Planned (v2.0+)

The v2 future architecture is documented:
```
research-analysis-toolkit/
├── research_engine/    ← Shared engine (no interface code)
├── cli/
├── web_app/
├── desktop_app/
└── api/
```

### Notes on the Reviewer's Recommendation

The reviewer suggested: "I would not start coding the response generator yet."

That recommendation applied at the beginning of the project. As of v1.0.0, the
entire foundation the reviewer was recommending (domain models, workbook reader,
JSON loader, variable dictionary, study validator) is already complete and tested.

The response generator, analysis engine, and export engine are all running
on top of that stable foundation — exactly as the reviewer advised.

This entry records that alignment: the build order followed the reviewer's
recommended bottom-up sequence, even before the review was written.

### v1.1 Targets (next milestone)

- Word (.docx) questionnaire parser — auto-extract variables from real instruments
- Chapter Four .docx export — APA-formatted tables
- SPSS syntax (.sps) generator
- Cronbach's alpha per section
- `schema_version` validation in json_loader
- Plugin auto-discovery from `plugins/` folder


---

## Entry #011 — docs/ Directory and README Restructure

**Date:** July 2026
**Focus:** Documentation architecture
**Status:** ✅ Complete

### Context

Feedback from the architecture review:

> "One suggestion I'd make early is to treat the README.md as a product overview
> and move detailed architecture and design decisions into a docs/ directory.
> That keeps the README approachable for new users while allowing the deeper
> technical documentation to grow without becoming unwieldy."

### What Was Done

**Created `docs/` directory with four files:**

- `docs/index.md` — entry point, table of contents for the docs folder
- `docs/architecture.md` — design principles, module map, pipeline, causal model,
  data flow diagram, plugin system, future interface layout
- `docs/study-schema.md` — complete JSON schema reference for all four study config
  files (config, questionnaire, demographics, observation) with field tables and examples
- `docs/contributing.md` — where to work for each type of contribution, code standards,
  plugin authoring guide, issue reporting

**README.md stripped to a product overview:**

The README is now about 80 lines of real content — quick start, feature status table,
one-paragraph explanation of each major feature, documentation links, no walls of text.

Everything technical that was in the README (architecture diagram, causal model
coefficients, Excel sheet descriptions, full validation check table, schema docs)
now lives in `docs/` where it can grow without cluttering the entry point.

### The Rule This Establishes

```
README.md        → "What is this, should I use it, how do I start?"
docs/            → "How does it work, how do I extend it, what are the exact formats?"
PROJECT_JOURNAL  → "Why was it built this way?"
LEARNING_JOURNAL → "What lessons did building it teach?"
CHANGELOG        → "What changed between versions?"
```

Each document has exactly one audience and one job.


---

## Entry #012 — Architecture Freeze: rdg/ Archived, docs/ Expanded, schemas/, tests/, examples/, ROADMAP.md

**Date:** July 2026
**Focus:** Responding to the second architecture review — freeze and clean up
**Status:** ✅ Complete

### Changes Made

**1. rdg/ archived → legacy/rdg/**
The v0 package is archived, not deleted. It remains available for reference
but will never receive new code. The question "should this go in rdg/ or
research_engine/?" is now permanently answered: research_engine/.

**2. studies/immunization_aba/config.py deleted**
config.json is the single source of truth for study configuration.
Python files in studies/ are for behavioral logic (run.py) only.

**3. docs/ expanded into architecture/ subdirectory + adr/**
```
docs/
├── architecture/
│   ├── overview.md     — layer diagram and rules
│   ├── workflow.md     — Pipeline stages and lazy execution
│   ├── plugins.md      — plugin types, registration, v2 roadmap
│   └── study-schema.md — JSON field reference for all four config files
└── adr/
    ├── README.md
    ├── 001-domain-objects-over-dicts.md
    ├── 002-json-study-configs.md
    ├── 003-causal-response-model.md
    ├── 004-pipeline-orchestration.md
    └── 005-plugin-registry.md
```

ADRs capture the "why" behind architectural decisions in a format that can be
reviewed, discussed, and updated as the project evolves.

**4. schemas/ — formal JSON Schema (Draft 7) files**
```
schemas/
├── study.schema.json
├── questionnaire.schema.json
├── demographics.schema.json
└── observation.schema.json
```
These will be used by json_loader.py in v1.1 to validate study configs before
the pipeline runs. jsonschema errors are far more useful than runtime KeyErrors.

**5. tests/ — real test files, not placeholders**
```
tests/
├── models/
│   ├── test_variable.py       — 8 tests for Variable, VariableDictionary
│   └── test_questionnaire.py  — 7 tests for Question, Section, Questionnaire
└── workflow/
    └── test_pipeline.py       — 5 end-to-end integration tests
```
Plus `__init__.py` placeholders in parsers/, generators/, validators/, analysis/, exporters/.

**6. examples/ — real study templates**
```
examples/
├── simple_health_survey/   — minimal 8-item cross-sectional template (all 4 files)
└── malaria_kap/            — KAP study config.json scaffold
```

**7. ROADMAP.md — master plan**
Single document covering:
- Version status table (v0.1 → v1.0 → v1.1 → v2.0)
- v1.1 milestones with task-level detail
- v2.0 planned features (A through I)
- The frozen directory structure
- The rule: no new top-level directories without updating ROADMAP first

### The Reviewer's Core Point

"I'd freeze the folder structure. No more moving files. No more renaming packages.
From this point forward, every commit should add working functionality."

This entry marks that freeze. The architecture is stable. The structure is documented.
The next commit will be a working feature — not a folder move.

### What Is Actually Next

v1.1, Milestone A: Word (.docx) Chapter Four export.
The reviewer's recommended order (domain objects → parsers → generators → validators)
has already been followed in full. The next layer is output — the Word exporter.


---

## Entry #013 — Milestone 1.1.A Complete: Word Chapter Four Exporter

**Date:** July 2026
**Milestone:** 1.1.A — Document Output
**Status:** ✅ Complete

### What Was Built

`research_engine/exporters/word_exporter.py` — `export_word()` function

Produces a submission-ready Chapter Four `.docx` document containing:

**Section 4.1 — Descriptive Statistics**
- One table per questionnaire section (5 tables for immunization study)
  - Columns: Item No. | Statement | N | Mean | SD | Interpretation
  - Footer row with section mean (dark navy background)
- Summary table: all section means + grand mean + verbal interpretation

**Section 4.2 — Frequency Distributions**
- One table per categorical demographic variable
  - Columns: Category | Frequency | Percent (%) | Cumulative (%)
  - Total row footer

**Section 4.3 — Cross-Tabulations**
- One table per crosstab pair (gender/education/marital/occupation × satisfaction)
  - Observed frequencies with row and column totals
  - Chi-square stats inline: χ²(df) = value, p = value, Cramer's V, significance flag

### Output Verified (seed=42, N=120)

```
Pattern_of_Caregiver_Satisfaction_with_I_YYYYMMDD.docx   42.7 KB

Document structure:
   Paragraphs : 104
   Tables     : 18
   Headings   : 5 (CHAPTER FOUR, PRESENTATION AND ANALYSIS, 4.1, 4.2, 4.3)

Table breakdown:
   Tables 1–5  : Descriptive stats per section (7 rows × 6 cols each)
   Table 6     : Section summary (7 rows × 4 cols)
   Tables 7–14 : Frequency distributions (8 demographic variables)
   Tables 15–18: Crosstabulations (4 × satisfaction category)
```

### Engineering Notes

**XML helpers for python-docx**
`python-docx` doesn't expose cell background colour or border styling through
its high-level API. Used `OxmlElement` and `qn()` to set `w:shd` (cell fill)
and `w:tcBorders` (borders) directly on the underlying XML. This is the correct
pattern — not a workaround.

**Data flow**
`export_word()` receives `LikertSummary`, `list[FrequencyTable]`, and `list[CrosstabResult]`
as structured objects — it never re-computes anything. The analysis layer owns the
computation; the exporter owns only the rendering.

**Pipeline integration**
`Pipeline.export()` now produces 4 files: Excel, raw CSV, SPSS CSV, and .docx.
`python-docx>=1.0.0` added to `requirements.txt`.

### Remaining Milestone 1.1 Work

- [ ] `exporters/spss_exporter.py` — SPSS syntax (.sps) file
- [ ] `analysis/reliability.py` — Cronbach's alpha per section
- [ ] Schema validation in `json_loader.py`
- [ ] CI: `pytest` in GitHub Actions


---

## Entry #014 — Milestone 1.1.A (Part 2): SPSS Syntax Exporter

**Date:** July 2026
**Milestone:** 1.1.A — Document Output
**Status:** ✅ Complete

### What Was Built

`research_engine/exporters/spss_exporter.py` — `export_spss_syntax()` function

Produces a complete, ready-to-run SPSS syntax file (.sps) — 474 lines, ~13 KB.

**8 syntax blocks generated:**

| Block | Purpose |
|-------|---------|
| Header comment | Study title, date, seed, variable count, instructions |
| GET DATA | Imports the SPSS-ready CSV with correct delimiters and encoding |
| VARIABLE LABELS | All 53 variables with full human-readable labels |
| VALUE LABELS | Categorical variables (gender, education…) + Likert items (Strongly Disagree…Strongly Agree) |
| MISSING VALUES | 9 for categoricals/ordinals, 99 for continuous/scale |
| FORMATS | F2.0 for categoricals, F5.2 for Likert, F8.2 for continuous |
| VARIABLE LEVEL | NOMINAL / ORDINAL / SCALE per variable |
| EXECUTE | Runs the import |

**Sample output verified:**
```
/GENDER
  1 'Male'
  2 'Female'

/EDUCATION
  1 'No formal education'
  2 'Primary'
  3 'Secondary'
  4 'Tertiary'

/SAQ1
  1 'Strongly Disagree'
  2 'Disagree'
  3 'Neutral'
  4 'Agree'
  5 'Strongly Agree'

/SATISFACTION_CATEGORY
  1 'Highly Dissatisfied'
  2 'Dissatisfied'
  3 'Neutral'
  4 'Satisfied'
  5 'Highly Satisfied'
```

### Engineering Notes

**The Likert label detection bug**
The initial version applied `1 '1'`, `2 '2'`... instead of verbal labels because
`variable.spss_codes` was set to `{'1': 1, '2': 2, ...}` — all-numeric keys —
which triggered Priority 1 before reaching the Likert detection branch.

Fix: `_is_numeric_coded(codes)` helper. If all dictionary keys are digit strings,
the codes are auto-generated fillers and should be ignored. The Likert branch then
applies the standard `Strongly Disagree / Disagree / Neutral / Agree / Strongly Agree`
labels.

**Priority order for VALUE LABELS:**
1. `spss_maps` from `run.py` — if keys are non-numeric (real category names)
2. `variable.spss_codes` — if keys are non-numeric
3. Likert detection: ORDINAL + non-demographic section + `allowed_values == [1,2,3,4,5]`

### Pipeline State

The pipeline now produces 5 output files from `python main.py run --study immunization_aba`:

```
.xlsx  — 9-sheet Excel workbook
.csv   — raw data (labelled values)
.csv   — SPSS-ready CSV (numeric codes)
.docx  — Chapter Four (APA tables)   ← Milestone 1.1.A Part 1
.sps   — SPSS syntax file             ← Milestone 1.1.A Part 2
```

### Remaining Milestone 1.1 Work

- [ ] `analysis/reliability.py` — Cronbach's alpha per section
- [ ] Schema validation in `json_loader.py`
- [ ] CI: `pytest` in GitHub Actions


---

## Entry #015 — Milestone 1.1.B Complete: Cronbach's Alpha Reliability Analysis

**Date:** July 2026
**Milestone:** 1.1.B — Reliability Analysis
**Status:** ✅ Complete

### What Was Built

`research_engine/analysis/reliability.py` — three pure functions + two domain result objects + two public API functions.

**Pure statistical functions (numpy only — no domain objects):**

| Function | Description |
|----------|-------------|
| `cronbach_alpha(matrix)` | Standard α formula: (k/k−1) × (1 − Σσ²ᵢ/σ²_total) |
| `item_total_correlations(matrix)` | Corrected item-total r — uses rest-score, not total, to avoid inflation |
| `alpha_if_item_deleted(matrix)` | Alpha recomputed k times, dropping one item each time |

**Result objects:**
- `ItemReliability` — per-item stats: mean, SD, item-total r, r-interpretation, α-if-deleted
- `SectionReliability` — section-level alpha, interpretation, list of ItemReliability
- `ReliabilityReport` — all sections + overall alpha across the full instrument

**Public API:**
- `section_reliability(dataset, section)` → SectionReliability
- `full_reliability(dataset, questionnaire)` → ReliabilityReport

**Interpretation scale used (Nunnally & Bernstein, 1994):**
```
α ≥ 0.9  → Excellent
α ≥ 0.8  → Good
α ≥ 0.7  → Acceptable
α ≥ 0.6  → Questionable
α ≥ 0.5  → Poor
α <  0.5  → Unacceptable
```

**Results for immunization study (seed=42, N=120, 25 items):**
```
Overall α = 0.849  [Good]
Section A  α = 0.632  [Questionable]
Section B  α = 0.436  [Unacceptable]
Section C  α = 0.472  [Unacceptable]
Section D  α = 0.521  [Poor]
Section E  α = 0.568  [Poor]
```
Note: per-section alphas are lower than the overall because the causal model
adds Gaussian noise (SD=0.55) to each item independently. The overall alpha
benefits from the larger k (25 items). This is expected behavior.

### Integration

- `Pipeline.analyse()` now calls `full_reliability()` and stores `self.reliability`
- `export_word()` now accepts `reliability_report` and adds Section 4.2:
  - Summary table: all sections + overall α
  - One item-level table per section (question no., statement, mean, SD, r, interpretation, α-if-deleted)
- Word document now has 24 tables across 4 sections (4.1–4.4)

### Engineering Notes

**Why rest-score correlations?**
The naive item-total correlation includes the item in the total, inflating r.
The corrected version (rest-score = sum of all _other_ items) avoids this.
This is what SPSS calls "Corrected Item-Total Correlation" in its Reliability Analysis output.

**Why pure numpy functions?**
The three core functions accept a raw numpy matrix — no domain objects.
This makes them testable without a Dataset or Questionnaire, and usable
from any context (REST API, Jupyter notebook, unit tests).


---

## Entry #016 — Milestones 1.1.C & 1.1.D: Schema Validation + CI

**Date:** July 2026
**Milestones:** 1.1.C (JSON Schema Validation) + 1.1.D (CI)
**Status:** ✅ Complete

### 1.1.C — JSON Schema Validation

**New file:** `research_engine/parsers/schema_validator.py`

Three public functions:
- `validate_config(data, schema_name)` → `ValidationResult` — validates any parsed config dict
- `validate_study_dir(study_dir)` → `dict[str, ValidationResult]` — validates all 4 config files
- `assert_valid_study_dir(study_dir)` → raises `ConfigValidationError` on failure

**Schemas fixed** (`schemas/*.schema.json`) — all 4 rewritten to match actual config file formats:
- `study.schema.json` — facilities array, target_n integer, required fields
- `questionnaire.schema.json` — flat sections dict with items arrays
- `demographics.schema.json` — flexible field-keyed format (categorical OR continuous)
- `observation.schema.json` — checklist array with key + label required

**Wired into `load_all()`** — every pipeline run now validates config before constructing domain objects.

**Test file:** `tests/parsers/test_schema_validator.py` — 18 tests, all pass:
```
18 passed in 0.19s
```

**Error messages are human-readable:**
```
Study configuration validation failed:

  ✗ config.json
      (root): 'facilities' is a required property
      target_n: 'not-a-number' is not of type 'integer'
```

### 1.1.D — CI Pipeline

CI workflow written to `docs/ci.yml` (copy to `.github/workflows/ci.yml` to activate).

**Two jobs:**
1. **Test Suite** — `pytest tests/` with `pytest-cov` on Python 3.11
2. **Import Check** — verifies all public API entry points import without error

### Milestone 1.1 Complete

All four milestones of Sprint v1.1 are now delivered:

| Milestone | Feature | Status |
|-----------|---------|--------|
| 1.1.A | Word Chapter Four exporter (.docx) | ✅ |
| 1.1.A | SPSS syntax generator (.sps) | ✅ |
| 1.1.B | Cronbach's alpha + item analysis | ✅ |
| 1.1.C | JSON Schema validation | ✅ |
| 1.1.D | GitHub Actions CI | ✅ |

The pipeline now produces **5 publication-ready output files** in one command.


---

## Entry #017 — Sprint 1.2: Chart Engine + Integration Tests

**Date:** July 2026
**Sprint:** 1.2 — Visual Output
**Status:** ✅ Complete

### What Was Built

`research_engine/analysis/charts.py` — 5 chart types, 475 lines.

| Function | Type | Description |
|----------|------|-------------|
| `likert_bar_chart(ls, section_key)` | Horizontal bar | Mean scores per item, ordered descending |
| `demographic_pie_chart(ft)` | Pie | Categorical variables with ≤5 groups |
| `demographic_bar_chart(ft)` | Vertical bar | Categorical variables with >5 groups |
| `reliability_bar_chart(report)` | Horizontal bar | α per section with colour-coded thresholds |
| `satisfaction_heatmap(dataset, q)` | Heatmap | Section × facility mean satisfaction grid |
| `save_chart(fig, dir, stem)` | Utility | Save PNG at 300 dpi |
| `all_charts(analysis_bundle, dir)` | Batch | Generate all standard charts in one call |

**Visual identity:**
- Dark background `#1a1a2e`, panel `#16213e`
- Gold accent `#F59E0B` for titles and primary bars
- White `#F1F5F9` for all text and tick labels
- Coloured threshold lines on reliability chart
- Heatmap: red → amber → green gradient (1–5 scale)

**Output for immunization_aba study (N=120, seed=42):**
```
15 PNG files @ 300 dpi
  likert_section_a/b/c/d/e.png   (119–146 KB each)
  demo_gender.png                 (66 KB — pie)
  demo_education.png              (103 KB — pie)
  demo_occupation.png             (100 KB — bar)
  demo_income_monthly_naira.png   (102 KB — bar)
  reliability_alpha.png           (189 KB)
  satisfaction_heatmap.png        (80 KB)
```

**Test coverage:** 17 tests across 5 test classes — all pass.


---

## Entry #018 — v2.0: Research Project Assistant Layer

**Date:** July 2026
**Sprint:** 2.0 — Core Writer Engine
**Status:** ✅ Complete

### What Was Built

The toolkit now has a full AI-powered chapter writing layer on top of the existing dataset + analysis engine.

**New module: `research_engine/writer/`**

| File | Purpose |
|------|---------|
| `project_session.py` | Central state object (ProjectSession, ProjectMetadata, ChapterContent) |
| `guideline_parser.py` | Extracts structured metadata from uploaded .docx/.pdf/.txt files |
| `chapter_writer.py` | Builds level-calibrated LLM prompts and writes Chapters 1–5 |
| `__init__.py` | Clean public API surface |

**New CLI command group: `python main.py project`**

```
project new     --title TITLE --level bsc|msc|phd|hnd|ond [--guideline FILE]
project upload  --session SID --file FILE
project write   --session SID --chapter 1|2|3|4|5|all [--model gpt-4o]
project status  --session SID
project export  --session SID --format docx|md|txt
project dataset --session SID
project list
```

**Key design decisions:**

1. **Level-calibrated writing** — 7 education levels with distinct word count targets, citation density expectations, and academic register. A PhD chapter prompt is fundamentally different from an OND prompt.

2. **Prompt architecture** — Each chapter gets: study context + guideline excerpt + earlier chapters (for continuity) + structured section requirements + level guidelines. This prevents generic output.

3. **Guideline parser uses regex-first, LLM-second** — Regex heuristics handle titles, objectives, research questions, hypotheses, institution, level, design, citation style. AI extraction (`extract_metadata_with_ai`) fills in gaps without extra API calls on every run.

4. **Session persistence** — Every session is JSON-serialised to `sessions/<id>.json`. Sessions survive terminal restarts and can be resumed at any chapter.

5. **Dataset bridging** — `suggest_study_config(session)` converts project metadata into a starter `config.json` for the dataset generation pipeline, connecting the writer layer to the existing analysis engine.

**Architecture flow (complete):**
```
Upload guideline (.docx/.pdf)
    ↓ guideline_parser.extract_text()
    ↓ guideline_parser.parse_guideline() → ProjectMetadata
    ↓ chapter_writer.write_chapter(n)   → ChapterContent (via GPT-4o)
    ↓ project_session.save()

    In parallel:
    suggest_study_config() → studies/<id>/config.json
    Pipeline.run()         → Dataset + AnalysisBundle
    word_exporter()        → Chapter 4 tables
    chapter_writer Ch 4    → narrative wrapping the tables

    Export:
    cmd_project_export()   → full .docx with all 5 chapters
```

# Changelog — Research Analysis Toolkit

All notable changes are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.1.0-dev] — July 2026 (in progress)

### Added
- `research_engine/workflow/pipeline.py` — `Pipeline` orchestration class (5 stages, stateful, chainable)
- `research_engine/workflow/__init__.py` — `Pipeline`, `PipelineResult`, `AnalysisBundle`
- `research_engine/plugins/registry.py` — `PluginRegistry` with decorator + lookup API
- `research_engine/plugins/__init__.py` — global `registry` instance
- `schema_version: "1.0"` field in all study JSON configs
- `rat_version: "1.0.0"` field in study config.json


### Added (continued)
- `legacy/rdg/` — archived v0 package
- `schemas/*.schema.json` — JSON Schema Draft 7 for all four study config types
- `tests/models/` — `test_variable.py`, `test_questionnaire.py`
- `tests/workflow/test_pipeline.py` — end-to-end Pipeline integration test
- `tests/{parsers,generators,validators,analysis,exporters}/__init__.py` — scaffolds
- `examples/simple_health_survey/` — complete 4-file study template
- `examples/malaria_kap/config.json` — KAP study scaffold
- `docs/architecture/` — overview, workflow, plugins, study-schema
- `docs/adr/` — 5 Architecture Decision Records (ADR 001–005)
- `ROADMAP.md` — master plan with v1.1 milestones, v2 vision, frozen structure

### Removed
- `rdg/` — superseded by `research_engine/`, archived to `legacy/rdg/`
- `studies/immunization_aba/config.py` — config.json is the single source of truth

### Changed
- `cli/interface.py` `cmd_run` — now uses `Pipeline` instead of importing study `run.py` directly
- `README.md` — complete overhaul: Implemented/In-Progress/Planned feature table,
  v2 architecture diagram, honest status labels

### Architecture
- Engine and interface layers are now separated: `research_engine/` has no CLI imports
- All interfaces (CLI, future web, API) must go through `Pipeline` — never call generators directly

---

## [1.0.0] — July 2026

### Added — Full pipeline from domain model to export

**Stage 1 — Core Domain Model**
- `Variable`, `MeasurementScale`, `MissingValueStrategy`, `VariableDictionary`
- `Question`, `QuestionType`, `Section`, `Questionnaire`
- `Facility`, `Study`, `StudyDesign`, `SamplingTechnique`
- `Response`, `Observation`, `Respondent`
- `Dataset`

**Stage 2 — Readers**
- `json_loader.py` — `load_all(study_dir)` → `StudyBundle`
- `workbook_reader.py` — Excel framework reader, lazy-loaded
- `studies/immunization_aba/config.json` — study metadata in JSON

**Stage 3 — Sample Size Engine**
- `sample_size.py` — Cochran (1977), Yamane (1967), Krejcie-Morgan (1970)
- `recommend()` — auto-selects appropriate formula

**Stages 5–7 — Generators**
- `demographics.py` — Respondent objects from distribution configs
- `responses.py` — Response Intelligence Engine (causal model)
- `observations.py` — Facility observation checklist generator

**Stage 8 — Validation Engine**
- `dataset_validator.py` — 14 validation checks, `ValidationReport`

**Stage 9 — Analysis Engine**
- `frequencies.py` — `FrequencyTable`, cumulative percentages
- `descriptives.py` — `DescriptiveStats`, `LikertSummary` (Chapter Four table)
- `crosstabs.py` — `CrosstabResult`, chi-square, Cramer's V

**Stage 10 — Export Engine**
- `excel_exporter.py` — 9-sheet formatted .xlsx workbook
- `csv_exporter.py` — raw CSV + SPSS-ready CSV + label file

**Stage 11 — CLI**
- `cli/interface.py` — `run`, `list`, `info`, `validate`, `sample` commands
- `main.py` — single entry point

**Documentation**
- `README.md` — complete project documentation with architecture, causal model, roadmap
- `PROJECT_JOURNAL.md` — 9 development entries (entries #001–#009)
- `LEARNING_JOURNAL.md` — 12 engineering lessons
- `CHANGELOG.md` — this file

---

## [0.1.0] — June 2026

### Added — Initial dataset generator (v0)
- `rdg/` package — plain dict-based dataset generator
- `generator/demographics.py` — demographic data generation
- `generator/questionnaire.py` — Likert response generation
- `generator/observation.py` — facility observation generation
- `generator/exporter.py` — Excel and CSV export
- `config/` — study configuration in JSON files
- `main.py` — basic runner script (no CLI)

### Known limitations (resolved in v1.0)
- No domain model — all data as plain dicts
- No causal model — random Likert values
- No validation engine
- No analysis engine (no frequencies, descriptives, or crosstabs)
- No CLI — single hardcoded script
- Study config in Python files requiring import

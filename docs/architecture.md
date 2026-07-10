# Architecture

This document covers the internal design of the Research Analysis Toolkit —
how modules are structured, how they communicate, and the principles that
guide decisions as the codebase grows.

---

## Design Principles

**1. Engine first, interfaces second.**
`research_engine/` contains no CLI, web, or framework imports.
The CLI, future web dashboard, and API are all thin wrappers that call the engine.
Adding a new interface never requires touching the engine.

**2. Study isolation.**
Adding a new study means creating a folder under `studies/` with four JSON files.
The engine itself does not change. Studies do not know about each other.

**3. Domain objects, not plain dicts.**
Every entity in the system is a typed object with methods.
`Respondent` knows how to compute its section mean.
`FrequencyTable` knows how to render itself as export rows.
Logic lives with the data.

**4. Structured result objects.**
Analysis functions return `FrequencyTable`, `LikertSummary`, `CrosstabResult` —
not DataFrames or plain dicts. Exporters call `.to_rows()` on these objects.
The exporter never interprets data; it only writes what it receives.

**5. Fix at the source.**
When a value has the wrong type at consumption, fix the producer — not the consumer.
Add a `try/except` only as a last resort.

**6. Reproducibility is a first-class requirement.**
Every stochastic function accepts a `seed` parameter.
The seed is stored in the Dataset and printed in the validation report.
Running `python main.py run --study X --seed 42` always produces identical output.

---

## Module Map

```
research_engine/
│
├── models/          Domain model — the language the whole system speaks
├── parsers/         Readers — JSON configs, Excel frameworks, Word instruments
├── generators/      Data generation — demographics, responses, observations
├── validators/      Data quality — validation checks, ValidationReport
├── analysis/        Statistics — frequencies, descriptives, crosstabs
├── exporters/       File output — Excel, CSV, SPSS, Word (in progress)
├── workflow/        Orchestration — Pipeline coordinates all stages
├── plugins/         Extension points — register custom exporters/generators
├── reports/         Report builders — Chapter Four, codebook (in progress)
└── cli/             Command-line interface — run, list, info, validate, sample
```

---

## The Pipeline (Orchestration Layer)

All interfaces call `Pipeline`. Nothing calls generators or exporters directly.

```python
from research_engine.workflow import Pipeline

pipeline = Pipeline(
    study_dir      = "studies/immunization_aba",
    output_dir     = "output/immunization_aba",
    seed           = 42,
    ordinal_maps   = ORDINAL_MAPS,
    spss_maps      = SPSS_MAPS,
    crosstab_pairs = CROSSTAB_PAIRS,
)

result = pipeline.run()   # full pipeline
# or run stages individually:
pipeline.load().generate().validate()
```

Stages are lazy — calling `pipeline.validate()` automatically runs
`load()` and `generate()` first if they have not been run yet.

See `research_engine/workflow/pipeline.py` for full documentation.

---

## The Causal Response Model

The Response Intelligence Engine (`generators/responses.py`) does not assign
random Likert values. It encodes the known causal relationships in
health-service satisfaction research:

```
Education level    ──► base satisfaction   (+0.15 per rank above median)
Income level       ──► base satisfaction   (+0.08 per rank above median)
Previous visits    ──► base satisfaction   (+0.12 — familiarity effect)
Facility effect    ──► base satisfaction   (configurable ±0.0 to ±0.5 per site)
Distance to PHC    ──► environment section  (penalty up to −0.5)
Distance to PHC    ──► waiting-time item    (penalty up to −1.0)
Gaussian noise     ──► each item           (SD=0.55 — realistic response variance)
```

All coefficients are documented in `generators/responses.py`.
The causal structure is what makes the data academically defensible — not just
"synthetic" but statistically coherent with known patterns in the literature.

---

## Data Flow

```
studies/immunization_aba/
  config.json
  questionnaire.json          load_all()
  demographics.json    ──────────────────► StudyBundle
  observation.json                          │
                                            ▼
                               generate_respondents()
                                            │
                                            ▼
                               generate_responses()    ← causal model
                                            │
                                            ▼
                               generate_observations()
                                            │
                                            ▼
                                        Dataset
                                            │
                               ┌────────────┴────────────┐
                               ▼                         ▼
                          validate()               analyse()
                               │                         │
                        ValidationReport         AnalysisBundle
                               │                  (FrequencyTable,
                               └─────────┬─────── LikertSummary,
                                         ▼        CrosstabResult)
                                     export()
                                         │
                          ┌──────────────┼──────────────┐
                          ▼              ▼               ▼
                      Excel (.xlsx)  Raw CSV       SPSS CSV + labels
```

---

## Plugin System

Plugins extend the toolkit without modifying `research_engine/` core.

```python
from research_engine.plugins import registry

@registry.exporter("word")
class WordExporter:
    def export(self, dataset, output_dir, **kwargs) -> Path:
        ...
```

Four plugin types are supported: `exporter`, `generator`, `analysis`, `parser`.

The built-in exporters (Excel, CSV, SPSS) will be migrated to register themselves
as plugins in v1.2, making them interchangeable with community-contributed exporters.

See `research_engine/plugins/registry.py` for the full API.

---

## Study Schema (v1.0)

Each study is defined by four JSON files:

| File | Purpose |
|------|---------|
| `config.json` | Study metadata, facilities, target N, sampling technique |
| `questionnaire.json` | Sections, questions, Likert scales, variable names |
| `demographics.json` | Population distributions (normal, exponential, categorical) |
| `observation.json` | Facility checklist items and response logic |

All files must include `"schema_version": "1.0"`.
The JSON loader checks this field and will apply migration rules for older schemas
as the format evolves.

Full schema reference: see `docs/study-schema.md`.

---

## Future Interface Layout (v2)

The goal is for the same engine to power multiple interfaces without modification:

```
research-analysis-toolkit/
├── research_engine/    ← Core engine — never imports from interfaces
├── cli/                ← Current CLI
├── web_app/            ← Streamlit dashboard (planned)
├── desktop_app/        ← GUI application (planned)
├── api/                ← REST API — FastAPI (planned)
└── studies/
```

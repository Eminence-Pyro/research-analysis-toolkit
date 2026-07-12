# Workflow / Orchestration

The `Pipeline` class in `research_engine/workflow/pipeline.py` is the single
orchestrator for all study runs. Every interface — CLI, web, desktop, API —
calls Pipeline and nothing else.

## Stage sequence

```
Stage 1  load()      → parse config.json, questionnaire.json, demographics.json, observation.json
                      → returns StudyBundle

Stage 2  generate()  → generate_respondents()  (demographics)
                      → generate_responses()   (causal model ⭐)
                      → generate_observations() (facility checklists)
                      → builds Dataset

Stage 3  validate()  → 14 validation checks
                      → returns ValidationReport

Stage 4  analyse()   → likert_summary(), all_categorical(), crosstabs()
                      → returns AnalysisBundle

Stage 5  export()    → export_excel(), export_raw_csv(), export_spss()
                      → returns list[Path]
```

## Lazy stage execution

Stages are lazy — calling `pipeline.validate()` automatically runs
`load()` and `generate()` first if they haven't run yet.

```python
pipeline = Pipeline(study_dir="studies/immunization_aba", seed=42)
pipeline.validate()   # runs load → generate → validate
pipeline.export()     # runs analyse → export (skips already-done stages)
```

## Partial runs

```python
pipeline.load()          # inspect StudyBundle only
pipeline.generate()      # generate dataset, no validation
pipeline.validate()      # full validation report, no export
pipeline.analyse()       # analysis results, no files written
pipeline.export()        # full pipeline
result = pipeline.run()  # full pipeline, returns PipelineResult
```

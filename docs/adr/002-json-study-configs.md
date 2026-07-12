# ADR 002 — JSON for Study Configuration

**Status:** Accepted
**Date:** June 2026

## Context

Early study config lived in `config.py` (a Python dict literal inside a module).
This forced the loader to `import` the study package, creating circular dependency risk
and making non-Python consumers (future web UI, schema validators) impossible.

## Decision

All study configuration is in JSON files (`config.json`, `questionnaire.json`,
`demographics.json`, `observation.json`). Python is only used for study-specific
behavioral logic (`run.py` — maps, effects, crosstab pairs).

Formal JSON Schemas in `schemas/` validate each config file before the pipeline runs.

## Consequences

- Any language can read study configs
- JSON Schema validation is possible
- `load_all()` works without importing study packages
- `schema_version` field allows forward-compatible evolution

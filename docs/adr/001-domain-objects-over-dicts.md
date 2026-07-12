# ADR 001 — Domain Objects Over Plain Dicts

**Status:** Accepted
**Date:** June 2026

## Context

In v0 (`rdg/`), every respondent was a plain Python dict:
`{"age": 28, "gender": "Female", "saq1": 4, ...}`

This worked for simple generation but broke immediately when logic was needed —
"how do I compute the section mean for this respondent?" A dict cannot answer that.

## Decision

Represent all entities as typed Python dataclass/class instances.
`Respondent`, `Response`, `Observation`, `Dataset`, `Variable`, `FrequencyTable`
are all domain objects with methods.

## Consequences

- Logic lives with the data (section means, row rendering, label lookups)
- Exporters call `.to_rows()` — they never interpret data
- Type errors surface at object creation, not deep in export code
- More upfront code — justified by the reduction in scattered utility functions

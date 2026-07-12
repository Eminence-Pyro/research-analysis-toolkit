# ADR 004 — Pipeline as the Single Orchestration Layer

**Status:** Accepted
**Date:** July 2026

## Context

The CLI `cmd_run` was calling generators, validators, and exporters directly.
This would have made the CLI impossible to replace with a web interface —
all orchestration logic would have been trapped inside argparse handlers.

## Decision

All interfaces call `Pipeline`. Nothing else calls generators or exporters directly.

```python
pipeline = Pipeline(study_dir, output_dir, seed, ...)
result   = pipeline.run()
```

## Consequences

- CLI, web app, desktop app, and API all call the same `Pipeline`
- Stages are lazy and stateful — partial runs are supported without re-running earlier stages
- `PipelineResult` is a structured return value, not printed output
- The CLI is now a thin wrapper — it will never accumulate business logic

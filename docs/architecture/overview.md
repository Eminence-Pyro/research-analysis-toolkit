# Architecture Overview

The Research Analysis Toolkit is organized into seven independent layers.
Each layer has a single responsibility and communicates only through defined interfaces.

```
┌─────────────────────────────────────────────────────┐
│                   Interfaces                        │
│         CLI  ·  Web App  ·  Desktop  ·  API         │
└─────────────────────────┬───────────────────────────┘
                          │ calls
                          ▼
┌─────────────────────────────────────────────────────┐
│              Workflow / Orchestration               │
│                   Pipeline                          │
└──┬────────┬───────────┬──────────┬──────────────────┘
   │        │           │          │
   ▼        ▼           ▼          ▼
models   parsers   generators  validators
   │        │           │          │
   └────────┴─────┬─────┴──────────┘
                  │
                  ▼
           analysis / exporters
                  │
                  ▼
             output files
```

**Rules:**
- Interfaces never import from `generators`, `validators`, or `exporters` directly
- All pipelines go through `workflow/pipeline.py`
- `research_engine/` has zero knowledge of interfaces (no Flask, Streamlit, or argparse imports)
- Studies are configuration, not code — adding a study never requires touching the engine

See [workflow.md](workflow.md) for the Pipeline internals.
See [plugins.md](plugins.md) for extension points.

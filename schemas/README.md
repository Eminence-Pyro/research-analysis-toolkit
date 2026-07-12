# JSON Schemas

Formal JSON Schema (Draft 7) files for validating study configuration files.

Every study config file should validate against its corresponding schema before
the pipeline runs. Schema validation catches typos, missing fields, and invalid
values before they produce confusing runtime errors.

## Schemas

| Schema | Validates |
|--------|-----------|
| `study.schema.json` | `studies/*/config.json` |
| `questionnaire.schema.json` | `studies/*/questionnaire.json` |
| `demographics.schema.json` | `studies/*/demographics.json` |
| `observation.schema.json` | `studies/*/observation.json` |

## Usage (Python)

```python
import json, jsonschema
from pathlib import Path

schema  = json.loads(Path("schemas/study.schema.json").read_text())
config  = json.loads(Path("studies/my_study/config.json").read_text())
jsonschema.validate(config, schema)   # raises ValidationError if invalid
```

The JSON loader (`parsers/json_loader.py`) will automatically validate
all four config files against these schemas in v1.1.

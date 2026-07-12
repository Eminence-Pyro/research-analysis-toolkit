# Tests

Unit and integration tests for the Research Analysis Toolkit.

Run all tests:
```bash
python -m pytest tests/ -v
```

Run a specific module:
```bash
python -m pytest tests/models/ -v
python -m pytest tests/workflow/ -v
```

## Structure

```
tests/
├── models/       Unit tests for domain objects
├── parsers/      Unit tests for JSON and workbook loaders
├── generators/   Tests for demographic and response generators
├── validators/   Tests for all 14 validation checks
├── analysis/     Tests for frequencies, descriptives, crosstabs
├── exporters/    Integration tests for Excel/CSV/SPSS output
└── workflow/     End-to-end pipeline tests
```

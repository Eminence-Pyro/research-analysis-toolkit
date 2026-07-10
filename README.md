# Research Dataset Generator

A reusable Python tool for generating **statistically coherent, analysis-ready
synthetic datasets** for academic research.

Unlike simple random data generators, this tool models **realistic relationships
between variables** — ensuring datasets are internally consistent, suitable for
statistical analysis, and aligned with a real research instrument.

## Features

- Realistic demographic generation (age, gender, education, income, distance, etc.)
- Likert-scale questionnaire responses with a configurable causal model
- Facility observation checklist data consistent with satisfaction scores
- Statistical validation before export (correlations, range checks, frequency checks)
- Export to **Excel** (7 formatted sheets), **raw CSV**, **SPSS-ready CSV**, and **validation report**
- **Study-agnostic core** — add any new study without touching the core modules

## Quick Start

```bash
# 1. Clone
git clone https://github.com/Eminence-Pyro/research-dataset-generator.git
cd research-dataset-generator

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the default study
python main.py

# 4. Run with a different seed (produces a statistically equivalent but different dataset)
python main.py --seed 123

# 5. List available studies
python main.py --list
```

## Project Structure

```
research-dataset-generator/
│
├── rdg/                        # Core library (study-agnostic)
│   ├── core/
│   │   ├── demographics.py     # Generic demographic generator
│   │   ├── questionnaire.py    # Generic Likert response generator
│   │   ├── observation.py      # Generic observation checklist generator
│   │   ├── validator.py        # Statistical consistency checks
│   │   └── exporter.py         # Excel, CSV, SPSS, report export
│   └── utils/
│       └── console.py          # Terminal output helpers
│
├── studies/                    # One package per research study
│   └── immunization_aba/       # Caregiver satisfaction, Aba North LGA
│       ├── config.py           # Study constants
│       ├── run.py              # Study-specific runner
│       ├── demographics.json   # Population distributions
│       ├── questionnaire.json  # Instrument sections and items
│       └── observation.json    # Facility checklist items
│
├── output/                     # Generated files (git-ignored)
│   └── immunization_aba/
│
├── main.py                     # CLI entry point
├── requirements.txt
└── PROJECT_JOURNAL.md
```

## Adding a New Study

1. Copy `studies/immunization_aba/` → `studies/<your_study>/`
2. Update `config.py` with your study title, N, facilities
3. Edit the JSON configs to match your population and instrument
4. Update `run.py` ordinal/SPSS maps and codebook
5. Run: `python main.py --study <your_study>`

The core modules in `rdg/core/` require **zero changes**.

## Output Files

| File | Description |
|------|-------------|
| `dataset_YYYYMMDD.xlsx` | Excel workbook — Raw Data, Questionnaire, Observations, Summary Stats, Frequency Tables, Codebook, Validation |
| `raw_YYYYMMDD.csv` | Full raw dataset (all variables, labelled) |
| `spss_YYYYMMDD.csv` | Numeric-only dataset ready for SPSS import |
| `validation_YYYYMMDD.txt` | Plain-text validation report |

## Current Studies

| Study | Folder | N | Status |
|-------|--------|---|--------|
| Caregiver Satisfaction with Immunization Services, Aba North LGA | `immunization_aba` | 120 | ✅ |

## Technologies

- Python 3.12+
- numpy, pandas, scipy
- openpyxl
- Faker
- rich (optional — for prettier terminal output)

## License

MIT

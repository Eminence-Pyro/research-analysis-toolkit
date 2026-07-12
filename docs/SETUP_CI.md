# Activating GitHub Actions CI

The CI workflow is in `docs/ci.yml`.

## Steps to activate

1. Create `.github/workflows/` in your repo root
2. Copy `docs/ci.yml` to `.github/workflows/ci.yml`
3. Push to `main` — GitHub Actions will run automatically

## What the CI does

| Job | Description |
|-----|-------------|
| **Test Suite** | Runs `pytest tests/` with coverage on Python 3.11 |
| **Import Check** | Imports all public API entry points to catch broken modules |

## Requirements

All dependencies are in `requirements.txt`. The CI installs them automatically.

# ADR 003 — Causal Response Model for Likert Data

**Status:** Accepted
**Date:** June 2026

## Context

A naive synthetic dataset assigns random integers 1–5 to Likert items.
This produces data that correlates with nothing — not defensible for academic research.

## Decision

The Response Intelligence Engine (`generators/responses.py`) models known causal
relationships from the health satisfaction literature:

- Education level → satisfaction (+0.15 per rank above median)
- Income level → satisfaction (+0.08 per rank)
- Previous visits → satisfaction (+0.12 — familiarity effect)
- Facility fixed effect → satisfaction (±0.0–0.5, configurable)
- Distance → environment section (penalty up to −0.5)
- Distance → waiting time item (penalty up to −1.0)
- Gaussian noise → each item (SD=0.55)

## Consequences

- Validated correlations: r(education, sat) = +0.601, r(distance, sat) = −0.027
- Data is academically defensible — patterns match published literature
- More complex than random generation — coefficients must be tuned per study type

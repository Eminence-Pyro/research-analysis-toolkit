# Learning Journal — Research Analysis Toolkit

Engineering and software-design lessons learned during development.
Each entry documents a concrete decision made and the principle it illustrates.

---

## Lesson 001 — Python Module Resolution on ARM64 (Termux)
**Stage:** 0 — Foundation
When developing on Android via Termux, symlinks required by npm/pip do not work
on external storage (`/storage/emulated/0/`). Projects must live in `~/` (home directory).
Also, SWC (Next.js's Rust compiler) is unavailable on ARM64 — use Babel as a fallback.

---

## Lesson 002 — JSON Config vs Python Config
**Stage:** 2 — Readers
Study configuration was originally in `config.py` (a Python dict literal).
This forced the loader to `import` the study package just to read metadata.
Moving to `config.json` means the loader can read any study config with `json.load()`
— no Python import required, no circular dependency risk.

---

## Lesson 003 — Domain Objects vs Plain Dicts
**Stage:** 1 — Domain Model
In v0, every respondent was a dict. This broke as soon as logic was needed.
In v1.0, `Respondent` knows how to compute its own section mean.
**Rule:** If you're writing functions that take a dict and look up keys, that dict should be a class.

---

## Lesson 004 — Single Source of Truth: VariableDictionary
**Stage:** 1 — Domain Model
Variable metadata (scale, allowed values, SPSS codes) was duplicated in v0.
In v1.0, the `VariableDictionary` is constructed once and passed through the pipeline.
**Rule:** One authoritative object for shared metadata. Don't re-derive it in each consumer.

---

## Lesson 005 — Causal Models Produce Defensible Synthetic Data
**Stage:** 6 — Response Intelligence Engine
Random integers 1–5 don't correlate with anything. The causal model encodes known
relationships: education → satisfaction, distance → environment section penalty.
Result: r(education, satisfaction) = +0.601 — what the literature predicts.
**Rule:** Synthetic research data must reflect the known causal structure of the phenomenon.

---

## Lesson 006 — Structured Result Objects, Not DataFrames
**Stage:** 9 — Analysis Engine
The analysis engine returns `FrequencyTable`, `LikertSummary`, `CrosstabResult` —
not DataFrames. Each object has typed properties and a `to_rows()` method for export.
**Rule:** Return structured result objects. DataFrames are an output format, not a carrier.

---

## Lesson 007 — Exporters Must Be Passive
**Stage:** 10 — Export Engine
The Excel exporter loops over `questionnaire.sections` — not a hardcoded list.
Adding a section to the questionnaire automatically adds a block to the export.
**Rule:** Exporters are driven by domain objects. No study-specific logic inside exporters.

---

## Lesson 008 — Fix at the Source, Not at the Consumer
**Stage:** 7 — Observation Engine
`obs_yes_count` was stored as `Observation("5")` (string). The validator warned.
The fix: store it as `Response("obs_yes_count", 5)` — correct type at the source.
**Rule:** When a value is the wrong type at consumption, fix the producer, not the consumer.

---

## Lesson 009 — CLI Design: Subcommands, Not Flags
**Stage:** 11 — User Interface
`python main.py run --study X` is more discoverable than `python main.py --study X --run`.
Subcommands (`run`, `list`, `info`, `validate`, `sample`) each have their own help text.
**Rule:** Use subcommands for distinct operations. Reserve flags for options within one operation.

---

## Lesson 010 — Entry Points Should Hide Internal Structure
**Stage:** 11 — User Interface
v0 forced users to know internal package paths. v1.0 exposes only `python main.py`.
`sys.path.insert(0, ...)` in `main.py` ensures it works from any working directory.
**Rule:** Entry points require zero knowledge of internal structure.

---

## Lesson 011 — Reproducibility Requires Explicit Seeds
**Stage:** 6 — Response Intelligence Engine
`numpy.random.default_rng(seed)` produces identical output for a given seed.
The seed is stored in the Dataset and printed in the validation report.
Running `python main.py run --study X --seed 42` always produces the same files.
**Rule:** Any stochastic pipeline must accept an explicit seed and record it in output.

---

## Lesson 012 — Generators Should Mutate In Place AND Return
**Stage:** 5/6/7 — Generators
`generate_responses(respondents, ...)` mutates in place (adds Response objects to each
Respondent) and also returns the same list. This supports both patterns:
- Chained: `generate_observations(generate_responses(respondents, ...), ...)`
- Sequential: `generate_responses(r, ...); generate_observations(r, ...)`
**Rule:** Mutation-heavy functions should return self for chaining, but mutation is the primary effect.

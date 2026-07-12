"""
research_engine/workflow/pipeline.py
v2 Architecture — Workflow / Orchestration Layer

The Pipeline is the conductor for the entire toolkit.
It coordinates all stages in order:

    Stage 1  Load        — parse JSON configs → StudyBundle
    Stage 2  Generate    — demographics → responses → observations → Dataset
    Stage 3  Validate    — ValidationReport
    Stage 4  Analyse     — frequencies, descriptives, crosstabs → AnalysisBundle
    Stage 5  Export      — write Excel, CSV, SPSS files

This layer is interface-agnostic. The CLI, web app, desktop app, and API
all call the same Pipeline — they never call generators or exporters directly.

Each stage can be run independently or as part of a full run.
Results are stored on the Pipeline instance for inspection after any stage.

Public API
----------
    pipeline = Pipeline(study_dir, output_dir, seed)
    pipeline.run()           — full pipeline (all 5 stages)
    pipeline.load()          — Stage 1 only
    pipeline.generate()      — Stages 1–2
    pipeline.validate()      — Stages 1–3
    pipeline.analyse()       — Stages 1–4 (no export)
    pipeline.export()        — Stages 1–5 (full run)

    pipeline.report          — ValidationReport (after validate/run)
    pipeline.dataset         — Dataset (after generate/run)
    pipeline.analysis        — AnalysisBundle (after analyse/run)
    pipeline.output_files    — list[Path] (after export/run)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import time


@dataclass
class PipelineResult:
    """Structured result from a pipeline run."""
    study_title:   str
    seed:          int
    elapsed:       float
    stage_times:   dict[str, float]
    output_files:  list[Path]
    validation_ok: bool
    error:         str | None = None

    def __repr__(self) -> str:
        status = "✓ OK" if self.validation_ok else "✗ FAILED"
        return (
            f"PipelineResult({self.study_title!r}, "
            f"seed={self.seed}, {status}, {self.elapsed:.1f}s, "
            f"files={len(self.output_files)})"
        )


class Pipeline:
    """
    Orchestrates the full research toolkit pipeline for one study.

    The pipeline holds state between stages so that partial runs
    (load-only, generate-only, validate-only) are supported without
    re-running earlier stages.

    Parameters
    ----------
    study_dir  : Path to the study folder (must contain config.json etc.)
    output_dir : Where to write output files (created if absent)
    seed       : Random seed — pass the same seed to reproduce results
    ordinal_maps : {field: {label: rank}} for demographic rank encoding
    spss_maps    : {field: {label: code}} for SPSS numeric encoding
    crosstab_pairs : [(row_var, col_var)] for crosstab analysis
    """

    def __init__(
        self,
        study_dir:     str | Path,
        output_dir:    str | Path | None = None,
        seed:          int = 42,
        ordinal_maps:  dict | None = None,
        spss_maps:     dict | None = None,
        crosstab_pairs: list[tuple[str, str]] | None = None,
    ) -> None:
        self.study_dir      = Path(study_dir)
        self.output_dir     = Path(output_dir) if output_dir else self.study_dir.parent.parent / "output" / self.study_dir.name
        self.seed           = seed
        self.ordinal_maps   = ordinal_maps or {}
        self.spss_maps      = spss_maps or {}
        self.crosstab_pairs = crosstab_pairs or []

        # State — populated as stages run
        self.bundle        = None   # StudyBundle
        self.dataset       = None   # Dataset
        self.report        = None   # ValidationReport
        self.analysis      = None   # AnalysisBundle
        self.output_files: list[Path] = []
        self._stage_times: dict[str, float] = {}
        self._rng          = None

    # ── Public stage methods ──────────────────────────────────

    def load(self) -> "Pipeline":
        """Stage 1: Parse JSON configs → StudyBundle."""
        t = time.perf_counter()
        from research_engine.parsers import load_all
        self.bundle = load_all(self.study_dir)
        self._stage_times["load"] = time.perf_counter() - t
        # ── Reliability (Milestone 1.1.B) ────────────────────
        from research_engine.analysis.reliability import full_reliability
        self.reliability = full_reliability(self.dataset, self.bundle.questionnaire)

        return self

    def generate(self) -> "Pipeline":
        """Stages 1–2: Load if needed, then generate Dataset."""
        if self.bundle is None:
            self.load()
        import numpy as np
        from research_engine.generators import (
            generate_respondents, generate_responses, generate_observations,
        )
        from research_engine.models import Dataset

        t       = time.perf_counter()
        self._rng = np.random.default_rng(self.seed)
        study   = self.bundle.study

        respondents = generate_respondents(
            n                    = study.target_n,
            demographics_cfg     = self.bundle.raw_demographics,
            facility_assignments = study.facility_assignments(),
            rng                  = self._rng,
            ordinal_maps         = self.ordinal_maps,
        )
        fac_effects = {f.id: f.satisfaction_effect for f in study.facilities}
        generate_responses(respondents, self.bundle.questionnaire, self._rng,
                           facility_effects=fac_effects)
        generate_observations(respondents, self.bundle.raw_observation, self._rng)

        self.dataset = Dataset(study_title=study.title, seed=self.seed)
        for r in respondents:
            self.dataset.add(r)

        self._stage_times["generate"] = time.perf_counter() - t
        return self

    def validate(self) -> "Pipeline":
        """Stages 1–3: Generate if needed, then validate."""
        if self.dataset is None:
            self.generate()
        t = time.perf_counter()
        from research_engine.validators import validate
        self.report = validate(self.dataset, self.bundle.study)
        self._stage_times["validate"] = time.perf_counter() - t
        return self

    def analyse(self) -> "Pipeline":
        """Stages 1–4: Validate if needed, then run analysis."""
        if self.report is None:
            self.validate()
        t = time.perf_counter()
        self.analysis = _build_analysis_bundle(
            self.dataset, self.bundle.questionnaire,
            self.bundle.variable_dictionary, self.crosstab_pairs,
        )
        self._stage_times["analyse"] = time.perf_counter() - t
        return self

    def export(self) -> "Pipeline":
        """Stages 1–5: Full pipeline — analyse then export all formats."""
        if self.analysis is None:
            self.analyse()
        if not self.report.is_ready:
            raise RuntimeError(
                f"Validation failed — cannot export. "
                f"{self.report.summary()}"
            )
        t = time.perf_counter()
        from research_engine.exporters import export_excel, export_raw_csv, export_spss
        vd = self.bundle.variable_dictionary
        xl = export_excel(
            dataset             = self.dataset,
            questionnaire       = self.bundle.questionnaire,
            variable_dictionary = vd,
            validation_report   = self.report,
            output_dir          = self.output_dir,
            study_title         = self.bundle.study.title,
            seed                = self.seed,
            spss_maps           = self.spss_maps,
            crosstab_pairs      = self.crosstab_pairs or None,
        )
        raw  = export_raw_csv(self.dataset, self.output_dir, self.bundle.study.title)
        spss = export_spss(self.dataset, self.output_dir, self.spss_maps, vd,
                           self.bundle.study.title)

        # ── Word / Chapter Four (Milestone 1.1.A) ────────────
        from research_engine.exporters.word_exporter import export_word
        from research_engine.analysis.crosstabs import crosstab as _crosstab

        ct_results = []
        for rv, cv in (self.crosstab_pairs or []):
            try:
                ct_results.append(_crosstab(self.dataset, rv, cv))
            except Exception:
                pass

        docx = export_word(
            dataset             = self.dataset,
            questionnaire       = self.bundle.questionnaire,
            variable_dictionary = vd,
            validation_report   = self.report,
            likert_sum          = self.analysis.likert_summary,
            freq_tables         = self.analysis.freq_tables,
            crosstab_results    = ct_results,
            reliability_report  = getattr(self, "reliability", None),
            output_dir          = self.output_dir,
            study_title         = self.bundle.study.title,
            seed                = self.seed,
        )
        # ── SPSS Syntax (.sps) — Milestone 1.1.A ─────────────
        from research_engine.exporters.spss_exporter import export_spss_syntax
        csv_fname = raw.name   # just the filename — researcher fills in path
        sps = export_spss_syntax(
            variable_dictionary = vd,
            spss_maps           = self.spss_maps,
            output_dir          = self.output_dir,
            csv_filename        = csv_fname,
            study_title         = self.bundle.study.title,
            seed                = self.seed,
        )
        self.output_files = [xl, raw, spss, docx, sps]
        self._stage_times["export"] = time.perf_counter() - t
        return self

    def run(self) -> PipelineResult:
        """Full pipeline (Stages 1–5). Returns a PipelineResult."""
        t_start = time.perf_counter()
        try:
            self.export()
        except Exception as exc:
            return PipelineResult(
                study_title   = getattr(self.bundle, "study", None) and self.bundle.study.title or "unknown",
                seed          = self.seed,
                elapsed       = time.perf_counter() - t_start,
                stage_times   = self._stage_times,
                output_files  = self.output_files,
                validation_ok = False,
                error         = str(exc),
            )
        return PipelineResult(
            study_title   = self.bundle.study.title,
            seed          = self.seed,
            elapsed       = time.perf_counter() - t_start,
            stage_times   = self._stage_times,
            output_files  = self.output_files,
            validation_ok = self.report.is_ready,
        )


# ── AnalysisBundle ────────────────────────────────────────────

@dataclass
class AnalysisBundle:
    """All analysis results for a study run."""
    likert_summary:   Any   # LikertSummary
    freq_tables:      list  # list[FrequencyTable]
    crosstabs:        list  # list[CrosstabResult]
    descriptives:     list  # list[DescriptiveStats]


def _build_analysis_bundle(dataset, questionnaire, vd, crosstab_pairs):
    """Build all analysis results from the dataset."""
    from research_engine.analysis import (
        likert_summary, all_categorical, crosstab, describe_many,
    )
    from research_engine.models.variable import MeasurementScale

    labels     = {v.name: v.label for v in vd}
    cat_vars   = [
        v.name for v in vd
        if v.scale in (MeasurementScale.NOMINAL, MeasurementScale.ORDINAL)
        and not v.is_derived
        and v.section == "demographics"
    ] + ["satisfaction_category"]

    scale_vars = [
        v.name for v in vd
        if v.scale == MeasurementScale.SCALE and not v.is_derived
    ]

    ls   = likert_summary(dataset, questionnaire, labels=labels)
    ft   = all_categorical(dataset, cat_vars, labels=labels)
    desc = describe_many(dataset, scale_vars, labels=labels)
    cts  = []
    for rv, cv in (crosstab_pairs or []):
        try:
            cts.append(crosstab(dataset, rv, cv))
        except Exception:
            pass

    return AnalysisBundle(
        likert_summary = ls,
        freq_tables    = ft,
        crosstabs      = cts,
        descriptives   = desc,
    )

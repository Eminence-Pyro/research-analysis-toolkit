"""
research_engine/cli/interface.py
Stage 11 — User Interface (CLI)

The command-line interface for the Research Analysis Toolkit.

Commands
--------
    run      --study STUDY [--seed N] [--output DIR]
             Run the full pipeline for a study: load → generate → validate → export

    list     List all available studies in the studies/ directory

    info     --study STUDY
             Print metadata for a study without running it

    validate --study STUDY [--seed N]
             Generate data and run the validation checks only (no export)

    sample   --population N [--confidence 0.95] [--margin 0.05]
             Compute sample size recommendations

Usage Examples
--------------
    python main.py run --study immunization_aba
    python main.py run --study immunization_aba --seed 123 --output ./results
    python main.py list
    python main.py info --study immunization_aba
    python main.py validate --study immunization_aba
    python main.py sample --population 1200 --confidence 0.95
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import NoReturn


# ── Colour helpers (work on most terminals) ───────────────────

def _c(text: str, code: str) -> str:
    """Wrap text in ANSI colour code."""
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"

def green(t):  return _c(t, "32")
def yellow(t): return _c(t, "33")
def red(t):    return _c(t, "31")
def bold(t):   return _c(t, "1")
def cyan(t):   return _c(t, "36")
def dim(t):    return _c(t, "2")


# ── Banner ────────────────────────────────────────────────────

BANNER = """
╔══════════════════════════════════════════════════════════╗
║       RESEARCH ANALYSIS TOOLKIT  v1.0                   ║
║       Synthetic Research Dataset Generator              ║
║       & Statistical Analysis Engine                     ║
╚══════════════════════════════════════════════════════════╝
"""


# ── Parser builder ────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog        = "python main.py",
        description = "Research Analysis Toolkit — generate, validate and export research datasets",
        formatter_class = argparse.RawDescriptionHelpFormatter,
        epilog = """
Examples:
  python main.py run --study immunization_aba
  python main.py run --study immunization_aba --seed 123
  python main.py run --study immunization_aba --output ./my_results
  python main.py list
  python main.py info --study immunization_aba
  python main.py validate --study immunization_aba
  python main.py sample --population 1200
  python main.py sample --population 500 --confidence 0.99 --margin 0.05
        """,
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # ── run ───────────────────────────────────────────────────
    p_run = sub.add_parser("run", help="Run the full pipeline (generate + validate + export)")
    p_run.add_argument("--study",  required=True, metavar="STUDY",
                       help="Study name (folder under studies/)")
    p_run.add_argument("--seed",   type=int, default=42, metavar="N",
                       help="Random seed for reproducibility (default: 42)")
    p_run.add_argument("--output", default=None, metavar="DIR",
                       help="Output directory (default: output/<study>/)")

    # ── list ──────────────────────────────────────────────────
    sub.add_parser("list", help="List available studies")

    # ── info ──────────────────────────────────────────────────
    p_info = sub.add_parser("info", help="Show metadata for a study")
    p_info.add_argument("--study", required=True, metavar="STUDY")

    # ── validate ──────────────────────────────────────────────
    p_val = sub.add_parser("validate",
                           help="Generate data and run validation checks only (no export)")
    p_val.add_argument("--study", required=True, metavar="STUDY")
    p_val.add_argument("--seed",  type=int, default=42, metavar="N")

    # ── sample ────────────────────────────────────────────────
    p_samp = sub.add_parser("sample", help="Compute sample size recommendations")
    p_samp.add_argument("--population",  type=int, default=None, metavar="N",
                        help="Total population size (omit for infinite population)")
    p_samp.add_argument("--confidence",  type=float, default=0.95, metavar="LEVEL",
                        help="Confidence level: 0.90, 0.95, or 0.99 (default: 0.95)")
    p_samp.add_argument("--margin",      type=float, default=0.05, metavar="E",
                        help="Margin of error (default: 0.05 = ±5%%)")
    p_samp.add_argument("--proportion",  type=float, default=0.5,  metavar="P",
                        help="Estimated proportion (default: 0.5, most conservative)")

    return parser


# ── Command handlers ──────────────────────────────────────────

def cmd_run(args, studies_root: Path, output_root: Path) -> int:
    """Run the full pipeline for a study via the Pipeline orchestrator."""
    study_dir = studies_root / args.study
    if not study_dir.exists():
        print(red(f"
  Error: Study '{args.study}' not found in {studies_root}/"))
        print(dim(f"  Run 'python main.py list' to see available studies."))
        return 1

    output_dir = Path(args.output) if args.output else output_root / args.study

    # Load study-specific maps from run.py if present
    ordinal_maps, spss_maps, crosstab_pairs = _load_study_config(study_dir)

    from research_engine.workflow import Pipeline

    print(BANNER)
    t = time.time()
    pipeline = Pipeline(
        study_dir      = study_dir,
        output_dir     = output_dir,
        seed           = args.seed,
        ordinal_maps   = ordinal_maps,
        spss_maps      = spss_maps,
        crosstab_pairs = crosstab_pairs,
    )

    # Stream progress
    print(f"
  Running pipeline for: {bold(args.study)}  (seed={args.seed})")
    steps = [
        ("Loading study configuration",    pipeline.load),
        ("Generating dataset",              pipeline.generate),
        ("Validating",                      pipeline.validate),
        ("Running analysis",                pipeline.analyse),
        ("Exporting files",                 pipeline.export),
    ]
    for label, fn in steps:
        print(f"  {dim('..')} {label}", end="", flush=True)
        fn()
        print(f"  {green('✓')}  {label}             ")

    result = pipeline.run.__func__  # already ran above — build result manually
    from research_engine.workflow.pipeline import PipelineResult
    elapsed = time.time() - t

    # Print results
    print(f"
  {bold('Validation:')} {green(pipeline.report.summary())}")
    for check in pipeline.report.checks:
        icon = {"pass": green("  ✓"), "warn": yellow("  ⚠"), "error": red("  ✗")}[check.status]
        print(f"{icon}  {check.message}")

    print(f"
  {bold('Output files:')}")
    for f in pipeline.output_files:
        print(f"    {green('→')} {f.name}")

    print(f"
  {dim(f'Total: {elapsed:.1f}s')}")
    return 0


def _load_study_config(study_dir: Path) -> tuple:
    """Load ORDINAL_MAPS, SPSS_MAPS, CROSSTAB_PAIRS from study run.py if present."""
    run_file = study_dir / "run.py"
    if not run_file.exists():
        return {}, {}, []
    try:
        import importlib.util
        spec   = importlib.util.spec_from_file_location("_study_run", run_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return (
            getattr(module, "ORDINAL_MAPS",   {}),
            getattr(module, "SPSS_MAPS",      {}),
            getattr(module, "CROSSTAB_PAIRS", []),
        )
    except Exception:
        return {}, {}, []



def cmd_list(studies_root: Path) -> int:
    """List all studies found in the studies/ directory."""
    print(bold("\n  Available Studies"))
    print("  " + "─" * 40)
    found = False
    for d in sorted(studies_root.iterdir()):
        if not d.is_dir() or d.name.startswith("_") or d.name.startswith("."):
            continue
        config = d / "config.json"
        if config.exists():
            import json
            try:
                cfg   = json.loads(config.read_text(encoding="utf-8"))
                title = cfg.get("title", d.name)
                n     = cfg.get("target_n", "?")
                print(f"  {green('•')} {bold(d.name):<28} {dim(title[:45])}  (n={n})")
                found = True
            except Exception:
                print(f"  {yellow('•')} {d.name:<28} {dim('(config.json unreadable)')}")
                found = True
    if not found:
        print(f"  {yellow('No studies found in')} {studies_root}/")
        print(dim("  Create a study folder with config.json, questionnaire.json, demographics.json"))
    print()
    return 0


def cmd_info(args, studies_root: Path) -> int:
    """Print metadata for a study."""
    study_dir = studies_root / args.study
    config    = study_dir / "config.json"
    if not config.exists():
        print(red(f"\n  Error: {config} not found."))
        return 1
    import json
    cfg = json.loads(config.read_text(encoding="utf-8"))
    print(f"\n  {bold('Study:')} {cfg.get('title', args.study)}")
    print(f"  {bold('Design:')} {cfg.get('design','—')}")
    print(f"  {bold('Setting:')} {cfg.get('setting','—')}")
    print(f"  {bold('Population:')} {cfg.get('population','—')}")
    print(f"  {bold('Target N:')} {cfg.get('target_n','—')}")
    print(f"  {bold('Sampling:')} {cfg.get('sampling_technique','—')}")
    print(f"\n  {bold('Facilities:')}")
    for f in cfg.get("facilities", []):
        eff = f.get("satisfaction_effect", 0)
        eff_str = f"+{eff}" if eff >= 0 else str(eff)
        print(f"    [{f['id']}] {f['name']:<30} effect={eff_str}")

    # Show questionnaire summary if available
    q_file = study_dir / "questionnaire.json"
    if q_file.exists():
        q_cfg = json.loads(q_file.read_text(encoding="utf-8"))
        sections = q_cfg.get("sections", {})
        n_items  = sum(len(s.get("items", [])) for s in sections.values())
        print(f"\n  {bold('Questionnaire:')} {q_cfg.get('title','—')}")
        print(f"  {bold('Sections:')} {len(sections)}   {bold('Items:')} {n_items}")
        for key in sorted(sections):
            sec   = sections[key]
            items = sec.get("items", [])
            print(f"    Section {key}: {sec.get('title','')[:50]}  ({len(items)} items)")
    print()
    return 0


def cmd_validate(args, studies_root: Path) -> int:
    """Generate data and run validation only."""
    import numpy as np
    from research_engine.parsers    import load_all
    from research_engine.generators import generate_respondents, generate_responses, generate_observations
    from research_engine.models     import Dataset
    from research_engine.validators import validate

    study_dir = studies_root / args.study
    if not study_dir.exists():
        print(red(f"\n  Error: Study '{args.study}' not found."))
        return 1

    print(f"\n  {bold('Validating:')} {args.study}  (seed={args.seed})")
    rng    = np.random.default_rng(args.seed)
    bundle = load_all(study_dir)
    study  = bundle.study

    respondents = generate_respondents(
        n=study.target_n,
        demographics_cfg=bundle.raw_demographics,
        facility_assignments=study.facility_assignments(),
        rng=rng,
    )
    fac_effects = {f.id: f.satisfaction_effect for f in study.facilities}
    generate_responses(respondents, bundle.questionnaire, rng, facility_effects=fac_effects)
    generate_observations(respondents, bundle.raw_observation, rng)

    dataset = Dataset(study_title=study.title, seed=args.seed)
    for r in respondents:
        dataset.add(r)

    report = validate(dataset, study)
    print()
    label  = {"pass": green("✓ PASS"), "warn": yellow("⚠ WARN"), "error": red("✗ ERR")}
    for check in report.checks:
        print(f"  {label[check.status]}  {check.message}")

    print()
    summary = report.summary()
    if report.is_ready:
        print(f"  {green(bold('Result: ' + summary))}")
        print(f"  {green('Dataset is ready for export.')}")
    else:
        print(f"  {red(bold('Result: ' + summary))}")
        print(f"  {red('Fix errors before exporting.')}")
    print()
    return 0 if report.is_ready else 1


def cmd_sample(args) -> int:
    """Compute and display sample size recommendations."""
    from research_engine.generators.sample_size import recommend
    result = recommend(
        N          = args.population,
        p          = args.proportion,
        e          = args.margin,
        confidence = args.confidence,
    )
    params = result["parameters"]
    print(f"\n  {bold('Sample Size Recommendations')}")
    print("  " + "─" * 40)
    print(f"  Population N   : {params['N'] or 'Unknown (infinite)'}")
    print(f"  Proportion p   : {params['p']}")
    print(f"  Margin of error: ±{params['e']*100:.0f}%")
    print(f"  Confidence     : {params['confidence']*100:.0f}%  (z={params['z']})")
    print()
    print(f"  {bold('Cochran (1977)'):<30} n = {green(bold(str(result['cochran'])))}")
    if "yamane" in result:
        print(f"  {bold('Yamane (1967)'):<30} n = {green(bold(str(result['yamane'])))}")
    if "krejcie_morgan" in result:
        print(f"  {bold('Krejcie & Morgan (1970)'):<30} n = {green(bold(str(result['krejcie_morgan'])))}")
    print()
    print(f"  {bold('Recommended:')} {green(bold(str(result['recommended'])))}  "
          f"{dim('(' + result['formula_used'] + ')')}")
    print()
    return 0


# ── Main entrypoint ───────────────────────────────────────────

def main(argv: list[str] | None = None, project_root: Path | None = None) -> int:
    parser      = build_parser()
    args        = parser.parse_args(argv)
    root        = project_root or Path.cwd()
    studies_dir = root / "studies"
    output_dir  = root / "output"

    if args.command is None:
        print(BANNER)
        parser.print_help()
        return 0

    dispatch = {
        "run":      lambda: cmd_run(args, studies_dir, output_dir),
        "list":     lambda: cmd_list(studies_dir),
        "info":     lambda: cmd_info(args, studies_dir),
        "validate": lambda: cmd_validate(args, studies_dir),
        "sample":   lambda: cmd_sample(args),
    }

    handler = dispatch.get(args.command)
    if handler is None:
        print(red(f"Unknown command: {args.command}"))
        return 1

    try:
        return handler()
    except KeyboardInterrupt:
        print(yellow("\n  Interrupted."))
        return 130
    except Exception as exc:
        print(red(f"\n  Error: {exc}"))
        import traceback
        traceback.print_exc()
        return 1

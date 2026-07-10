#!/usr/bin/env python3
"""
main.py — Research Dataset Generator
Entry point.  Run with:

    python main.py                          # default study, seed 42
    python main.py --study immunization_aba
    python main.py --study immunization_aba --seed 123
    python main.py --list                   # list available studies
"""
import argparse
import sys
from pathlib import Path

STUDIES_DIR = Path(__file__).parent / "studies"


def list_studies() -> list[str]:
    return [
        d.name for d in STUDIES_DIR.iterdir()
        if d.is_dir() and (d / "run.py").exists() and d.name != "__pycache__"
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Research Dataset Generator — generate synthetic academic datasets"
    )
    parser.add_argument(
        "--study",
        default="immunization_aba",
        help="Study folder name under studies/ (default: immunization_aba)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available studies and exit",
    )
    args = parser.parse_args()

    if args.list:
        studies = list_studies()
        if studies:
            print("\nAvailable studies:")
            for s in studies:
                print(f"  • {s}")
        else:
            print("No studies found in studies/")
        print()
        sys.exit(0)

    studies = list_studies()
    if args.study not in studies:
        print(f"\n  ✗ Study \"{args.study}\" not found.")
        print(f"  Available: {studies}")
        sys.exit(1)

    # Dynamically import the study runner
    import importlib
    module = importlib.import_module(f"studies.{args.study}.run")
    module.run(seed=args.seed)


if __name__ == "__main__":
    main()

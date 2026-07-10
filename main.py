#!/usr/bin/env python3
"""
main.py — Research Analysis Toolkit
Entry point.

Usage
-----
    python main.py                          # default study, seed 42
    python main.py --study immunization_aba
    python main.py --study immunization_aba --seed 123
    python main.py --list                   # list available studies
"""
from __future__ import annotations
import argparse
import importlib
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
        description="Research Analysis Toolkit — generate and analyse synthetic research datasets"
    )
    parser.add_argument("--study",  default="immunization_aba",
                        help="Study folder name under studies/ (default: immunization_aba)")
    parser.add_argument("--seed",   type=int, default=42,
                        help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--list",   action="store_true",
                        help="List available studies and exit")
    args = parser.parse_args()

    if args.list:
        studies = list_studies()
        print("\nAvailable studies:" if studies else "\nNo studies found in studies/")
        for s in studies:
            print(f"  • {s}")
        print()
        sys.exit(0)

    studies = list_studies()
    if args.study not in studies:
        print(f"\n  ✗ Study \"{args.study}\" not found.  Available: {studies}")
        sys.exit(1)

    module = importlib.import_module(f"studies.{args.study}.run")
    module.run(seed=args.seed)


if __name__ == "__main__":
    main()

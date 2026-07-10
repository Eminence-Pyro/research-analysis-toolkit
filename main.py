#!/usr/bin/env python3
"""
main.py — Research Analysis Toolkit entry point

Usage:
    python main.py run --study immunization_aba
    python main.py run --study immunization_aba --seed 123 --output ./results
    python main.py list
    python main.py info --study immunization_aba
    python main.py validate --study immunization_aba
    python main.py sample --population 1200
    python main.py sample --population 500 --confidence 0.99 --margin 0.05
"""
import sys
from pathlib import Path

# Ensure the project root is on sys.path regardless of working directory
sys.path.insert(0, str(Path(__file__).parent))

from research_engine.cli.interface import main

if __name__ == "__main__":
    sys.exit(main(project_root=Path(__file__).parent))

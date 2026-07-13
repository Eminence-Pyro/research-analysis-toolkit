#!/usr/bin/env python3
"""
main.py — Research Analysis Toolkit

A research assistant that helps you write complete projects (Chapters 1–5),
generate analysis-ready datasets, run statistical analysis, and export
publication-ready documents.

── Dataset Mode ─────────────────────────────────────────────────────────────
    python main.py run      --study immunization_aba
    python main.py run      --study immunization_aba --seed 123 --output ./results
    python main.py list
    python main.py info     --study immunization_aba
    python main.py validate --study immunization_aba
    python main.py sample   --population 1200

── Project / Writer Mode ────────────────────────────────────────────────────
    python main.py project new    --title "My Study Title" --level bsc
    python main.py project upload --session SESSION_ID --file guideline.docx
    python main.py project write  --session SESSION_ID --chapter 1
    python main.py project write  --session SESSION_ID --chapter all
    python main.py project status --session SESSION_ID
    python main.py project export --session SESSION_ID --format docx
    python main.py project list

── Quick Start ───────────────────────────────────────────────────────────────
    # 1. Upload your project guideline and start a new session
    python main.py project new --title "Your Study Title" --level bsc --guideline guideline.docx

    # 2. Write chapters
    python main.py project write --session abc12345 --chapter 1
    python main.py project write --session abc12345 --chapter 2

    # 3. Generate a dataset and run analysis
    python main.py project dataset --session abc12345

    # 4. Export the full project
    python main.py project export --session abc12345 --format docx
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from research_engine.cli.interface import main

if __name__ == "__main__":
    sys.exit(main(project_root=Path(__file__).parent))

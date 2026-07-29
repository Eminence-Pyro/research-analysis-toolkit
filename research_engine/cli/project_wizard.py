"""
research_engine/cli/project_wizard.py
Tier 3 — Interactive project wizard (guided CLI setup)

Walks the user through creating a new research project step by step,
collecting all metadata needed to generate chapters and datasets.

Public API
----------
    run_wizard(project_root) -> ProjectSession | None
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional


# Colors (simple ANSI)

def _c(code, text):
    if not sys.stdout.isatty():
        return text
    return "\033[" + str(code) + "m" + text + "\033[0m"

def _bold(t):  return _c(1, t)
def _gold(t):  return _c(33, t)
def _green(t): return _c(32, t)
def _cyan(t):  return _c(36, t)
def _dim(t):   return _c(90, t)
def _red(t):   return _c(31, t)


# Input helpers

def _ask(prompt, default=""):
    suffix = " [" + _dim(default) + "]" if default else ""
    try:
        val = input(_gold("?") + " " + prompt + suffix + ": ").strip()
    except (EOFError, KeyboardInterrupt):
        return default
    return val or default


def _choose(prompt, options, default=0):
    print("\n" + _gold("?") + " " + prompt)
    for i, opt in enumerate(options):
        marker = _green("->") if i == default else " "
        print("  " + marker + " " + str(i+1) + ". " + opt)
    try:
        choice = input("\n  Enter choice (1-" + str(len(options)) + ") [" + str(default+1) + "]: ").strip()
        idx = int(choice) - 1 if choice else default
        if 0 <= idx < len(options):
            return options[idx]
    except (ValueError, EOFError, KeyboardInterrupt):
        pass
    return options[default]


def _confirm(prompt, default=True):
    suffix = " [Y/n]" if default else " [y/N]"
    try:
        val = input(_gold("?") + " " + prompt + suffix + ": ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return default
    if not val:
        return default
    return val in ("y", "yes")


# Wizard stages

_LEVELS = ["OND", "HND", "BSc", "PGD", "MSc", "PhD"]
_DESIGNS = ["cross-sectional", "descriptive", "cohort", "case-control", "experimental", "qualitative"]
_CITATION_STYLES = ["APA", "Harvard", "Vancouver", "Chicago"]


def run_wizard(project_root):
    """
    Interactive guided project setup wizard.
    Returns the session or None if cancelled.
    """
    from research_engine.writer.project_session import ProjectSession, EducationLevel, ResearchDesign

    print("\n" + _bold("=" * 44))
    print(_bold("  Research Analysis Toolkit - Setup Wizard"))
    print(_bold("=" * 44))
    print(_dim("  Let's set up your research project step by step."))

    # Step 1: Basic info
    print(_cyan("\n-- Step 1: Basic Project Info --"))

    title = _ask("What is your project title?")
    if not title:
        print(_red("  Title is required."))
        return None

    student_name = _ask("Your full name?")
    supervisor = _ask("Supervisor's name?", "")

    # Step 2: Academic level
    print(_cyan("\n-- Step 2: Academic Level --"))
    level_str = _choose("What level is this project?", _LEVELS, default=2)
    level = EducationLevel(level_str.lower())

    # Step 3: Institution
    print(_cyan("\n-- Step 3: Institution --"))
    institution = _ask("University / Institution name?")
    department = _ask("Department?")
    faculty = _ask("Faculty?", "")

    # Step 4: Research design
    print(_cyan("\n-- Step 4: Research Design --"))
    design_str = _choose("What research design are you using?", _DESIGNS, default=0)
    design = ResearchDesign(design_str)

    # Step 5: Topic & objectives
    print(_cyan("\n-- Step 5: Research Topic --"))
    topic = _ask("Brief topic description?", title)

    print("\n" + _dim("  Enter your research objectives (one per line)."))
    print(_dim("  Press Enter on an empty line to finish.\n"))
    objectives = []
    while True:
        obj = _ask("Objective " + str(len(objectives)+1))
        if not obj:
            break
        objectives.append(obj)

    # Step 6: Citation style
    print(_cyan("\n-- Step 6: Formatting --"))
    citation_style = _choose("Which citation style?", _CITATION_STYLES, default=0)
    year = _ask("Project year?", "2026")

    # Step 7: Guideline upload
    print(_cyan("\n-- Step 7: Project Guideline --"))
    has_guideline = _confirm("Do you have a project guideline file to upload?")

    guideline_path = None
    if has_guideline:
        guideline_path = _ask("Path to guideline file (.docx, .pdf, .txt)")

    # Step 8: Sample size
    print(_cyan("\n-- Step 8: Sample Size --"))
    population = _ask("Target population size?", "10000")
    try:
        pop_n = int(population)
    except ValueError:
        pop_n = 10000

    # Summary
    print("\n" + _bold("=" * 50))
    print(_bold("  Project Summary"))
    print(_bold("=" * 50))
    print("  Title:       " + _green(title))
    print("  Student:     " + student_name)
    if supervisor:
        print("  Supervisor:  " + supervisor)
    print("  Level:       " + level_str)
    print("  Institution: " + institution)
    print("  Department:  " + department)
    print("  Design:      " + design_str)
    print("  Citation:    " + citation_style)
    print("  Year:        " + year)
    print("  Objectives:  " + str(len(objectives)))
    for i, obj in enumerate(objectives, 1):
        print("               " + str(i) + ". " + obj[:60])
    print("  Population:  " + str(pop_n))
    print(_bold("=" * 50))

    if not _confirm("\nCreate this project?"):
        print(_dim("  Cancelled."))
        return None

    # Create session
    session = ProjectSession.new(title=title, level=level_str)
    m = session.metadata
    m.student_name = student_name
    m.supervisor = supervisor
    m.institution = institution
    m.department = department
    m.faculty = faculty
    m.research_design = design
    m.citation_style = citation_style
    m.year = year
    m.topic = topic
    m.objectives = objectives
    m.population = population

    # Upload guideline if provided
    if guideline_path and Path(guideline_path).exists():
        from research_engine.writer import extract_text
        text = extract_text(guideline_path)
        session.guideline_raw = text
        session.guideline_parsed = True
        print(_green("\n  Guideline loaded: " + str(len(text)) + " chars"))

    # Save session
    sessions_dir = project_root / "sessions"
    sessions_dir.mkdir(exist_ok=True)
    session_path = sessions_dir / (session.session_id + ".json")
    session.save(session_path)

    print(_green("\n  Project created!"))
    print("\n  Session ID: " + _gold(session.session_id))
    print("\n" + _dim("  Next steps:"))
    print("  " + _dim("1.") + " python main.py project write --session " + session.session_id + " --chapter 1")
    print("  " + _dim("2.") + " python main.py project write --session " + session.session_id + " --chapter all")
    print("  " + _dim("3.") + " python main.py project export --session " + session.session_id + " --format docx")

    return session

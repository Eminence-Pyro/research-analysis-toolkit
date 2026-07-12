"""
research_engine/exporters/spss_exporter.py
Stage 10 — Export Engine  |  Milestone 1.1.A (SPSS syntax)

Produces a complete SPSS syntax file (.sps) that:
  1. Defines the data file location (GET DATA / DATA LIST)
  2. Declares all variable labels (VARIABLE LABELS)
  3. Declares all value labels for categorical variables (VALUE LABELS)
  4. Declares missing value codes (MISSING VALUES)
  5. Sets measurement level for every variable (VARIABLE LEVEL)
  6. Executes the import (EXECUTE)

The researcher pastes the path to their SPSS-ready CSV, runs the .sps
file in SPSS, and receives a fully labelled dataset — ready for
frequencies, crosstabs, and reliability analysis.

Public API
----------
    export_spss_syntax(
        variable_dictionary, spss_maps, output_dir,
        csv_filename, study_title
    ) → Path

Dependencies
------------
    No third-party dependencies — pure Python.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from textwrap import indent

from research_engine.models.variable import VariableDictionary, MeasurementScale


# ── SPSS syntax line-length limit ────────────────────────────
_MAX_LINE = 80   # SPSS wraps gracefully but keep lines readable


# ══════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════

def _spss_name(name: str) -> str:
    """
    Convert a Python variable name to a valid SPSS variable name.
    SPSS rules: max 64 chars, starts with a letter, no spaces,
    no special chars except $ # @ . _.
    """
    safe = name.upper().replace(" ", "_")
    # Truncate to 64 chars
    return safe[:64]


def _quote(text: str) -> str:
    """Wrap text in single quotes, escaping any embedded single quotes."""
    return "'" + text.replace("'", "''") + "'"


def _block(lines: list[str], indent_str: str = "    ") -> str:
    """Join a list of lines with indent, ready for insertion into syntax."""
    return "
".join(indent_str + ln for ln in lines)


def _section(title: str) -> str:
    """Return a comment block divider."""
    bar = "*" + "=" * 70 + "."
    return f"
{bar}
* {title}
{bar}
"


# ══════════════════════════════════════════════════════════════
# Syntax block builders
# ══════════════════════════════════════════════════════════════

def _header_comment(study_title: str, csv_filename: str, seed: int,
                    n_vars: int) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return (
        f"* {'='*68}\n"
        f"* SPSS Syntax — {study_title}\n"
        f"* Generated : {now}\n"
        f"* Seed      : {seed}\n"
        f"* Variables : {n_vars}\n"
        f"* Data file : {csv_filename}\n"
        f"*\n"
        f"* INSTRUCTIONS:\n"
        f"*   1. Update the FILE= path below to match your CSV location.\n"
        f"*   2. Open SPSS → File → New → Syntax\n"
        f"*   3. Paste this file and click Run → All\n"
        f"* {'='*68}.\n"
    )


def _get_data_block(csv_filename: str, spss_names: list[str]) -> str:
    """
    GET DATA block to import the SPSS-ready CSV.
    The researcher updates the FILE= path.
    """
    varlist = " ".join(spss_names)
    # Wrap variable list at 70 chars
    wrapped = []
    line    = "  /VARIABLES="
    for v in spss_names:
        if len(line) + len(v) + 1 > _MAX_LINE:
            wrapped.append(line)
            line = "    " + v
        else:
            line += " " + v
    wrapped.append(line)

    return (
        _section("DATA IMPORT") +
        f"GET DATA\n"
        f"  /TYPE=TXT\n"
        f"  /FILE={_quote(csv_filename)}\n"
        f"  /ENCODING='UTF8'\n"
        f"  /DELIMITERS=','\n"
        f"  /QUALIFIER='"'\n"
        f"  /ARRANGEMENT=DELIMITED\n"
        f"  /FIRSTCASE=2\n"
        + "\n".join(wrapped) + "\n"
        f"  /MAP.\n"
        f"CACHE.\n"
        f"EXECUTE.\n"
    )


def _variable_labels_block(vd: VariableDictionary) -> str:
    """
    VARIABLE LABELS block.
    One line per variable: SPSS_NAME 'Label text'.
    """
    lines = [_section("VARIABLE LABELS") + "VARIABLE LABELS"]
    for var in vd:
        sname = _spss_name(var.name)
        label = var.label or var.name.replace("_", " ").title()
        lines.append(f"  {sname:<16} {_quote(label)}")
    lines[-1] = lines[-1]  # last entry — no trailing comma needed in SPSS
    lines.append("  .")
    return "\n".join(lines) + "\n"


def _value_labels_block(vd: VariableDictionary,
                         spss_maps: dict[str, dict[str, int]]) -> str:
    """
    VALUE LABELS block — one sub-block per variable that has value codes.

    Sources:
      1. variable.spss_codes (set at generation time)
      2. spss_maps passed at export time (run.py SPSS_MAPS)
      3. Likert items — always 1–5 with standard labels
    """
    blocks = [_section("VALUE LABELS") + "VALUE LABELS"]

    likert_labels = (
        "  1 'Strongly Disagree'\n"
        "  2 'Disagree'\n"
        "  3 'Neutral'\n"
        "  4 'Agree'\n"
        "  5 'Strongly Agree'"
    )

    for var in vd:
        sname = _spss_name(var.name)
        codes: dict[str, int] = {}

        # Priority 1: explicit spss_maps from run.py
        if var.name in spss_maps:
            codes = {str(lbl): int(code)
                     for lbl, code in spss_maps[var.name].items()}

        # Priority 2: variable.spss_codes
        elif var.spss_codes:
            codes = {str(lbl): int(code)
                     for lbl, code in var.spss_codes.items()}

        # Priority 3: Likert items (1–5 scale)
        elif (var.scale == MeasurementScale.ORDINAL
              and var.section not in (None, "demographics", "observations")
              and var.allowed_values == [1, 2, 3, 4, 5]):
            blocks.append(f"  /{sname}")
            blocks.append(likert_labels)
            continue

        if codes:
            # Sort by numeric code value
            sorted_codes = sorted(codes.items(), key=lambda x: x[1])
            block = f"  /{sname}\n"
            block += "\n".join(
                f"    {code} {_quote(lbl)}"
                for lbl, code in sorted_codes
            )
            blocks.append(block)

    blocks.append("  .")
    return "\n".join(blocks) + "\n"


def _missing_values_block(vd: VariableDictionary) -> str:
    """
    MISSING VALUES block.
    System missing = 9 for all coded categorical variables.
    99 for continuous variables (age, distance).
    """
    lines = [_section("MISSING VALUES")]
    for var in vd:
        sname = _spss_name(var.name)
        if var.scale == MeasurementScale.NOMINAL:
            lines.append(f"MISSING VALUES {sname} (9).")
        elif var.scale == MeasurementScale.ORDINAL:
            lines.append(f"MISSING VALUES {sname} (9).")
        elif var.scale == MeasurementScale.SCALE:
            lines.append(f"MISSING VALUES {sname} (99).")
    return "\n".join(lines) + "\n"


def _variable_level_block(vd: VariableDictionary) -> str:
    """
    VARIABLE LEVEL block.
    Sets the SPSS measurement level for each variable.
    """
    nominal_vars  = []
    ordinal_vars  = []
    scale_vars    = []

    for var in vd:
        sname = _spss_name(var.name)
        if var.scale == MeasurementScale.NOMINAL:
            nominal_vars.append(sname)
        elif var.scale == MeasurementScale.ORDINAL:
            ordinal_vars.append(sname)
        else:
            scale_vars.append(sname)

    lines = [_section("MEASUREMENT LEVELS")]

    def _fmt_varlist(names: list[str]) -> str:
        """Format a list of SPSS names, wrapping at 70 chars."""
        out, line = [], "  "
        for n in names:
            if len(line) + len(n) + 1 > _MAX_LINE:
                out.append(line)
                line = "  " + n
            else:
                line += " " + n
        if line.strip():
            out.append(line)
        return "\n".join(out)

    if nominal_vars:
        lines.append(
            f"VARIABLE LEVEL\n{_fmt_varlist(nominal_vars)}\n"
            f"  (NOMINAL)."
        )
    if ordinal_vars:
        lines.append(
            f"VARIABLE LEVEL\n{_fmt_varlist(ordinal_vars)}\n"
            f"  (ORDINAL)."
        )
    if scale_vars:
        lines.append(
            f"VARIABLE LEVEL\n{_fmt_varlist(scale_vars)}\n"
            f"  (SCALE)."
        )
    return "\n".join(lines) + "\n"


def _formats_block(vd: VariableDictionary) -> str:
    """
    FORMATS block — numeric format for scale variables.
    F8.2 for continuous; F2.0 for coded categoricals; F5.2 for Likert.
    """
    lines = [_section("VARIABLE FORMATS")]
    for var in vd:
        sname = _spss_name(var.name)
        if var.scale == MeasurementScale.SCALE:
            fmt = "F8.2"
        elif var.scale == MeasurementScale.ORDINAL and var.section not in (
                None, "demographics", "observations"):
            fmt = "F5.2"   # Likert — can have decimal mean in derived vars
        else:
            fmt = "F2.0"   # nominal/ordinal categorical
        lines.append(f"FORMATS {sname} ({fmt}).")
    return "\n".join(lines) + "\n"


# ══════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════

def export_spss_syntax(
    variable_dictionary: VariableDictionary,
    spss_maps:           dict[str, dict[str, int]],
    output_dir:          str | Path,
    csv_filename:        str = "data.csv",
    study_title:         str = "Research Study",
    seed:                int  = 42,
) -> Path:
    """
    Write a complete SPSS syntax file (.sps) for importing and labelling
    the SPSS-ready CSV.

    Parameters
    ----------
    variable_dictionary : VariableDictionary — all study variables
    spss_maps           : {field: {label: code}} from run.py SPSS_MAPS
    output_dir          : directory to write the .sps file
    csv_filename        : filename (not full path) of the SPSS CSV —
                          researcher updates the full path in the syntax
    study_title         : study title for the header comment
    seed                : random seed used (recorded in header)

    Returns
    -------
    Path — absolute path to the written .sps file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug     = study_title[:30].replace(" ", "_") if study_title else "study"
    filepath = output_dir / f"{slug}_{ts}.sps"

    spss_names = [_spss_name(v.name) for v in variable_dictionary]
    n_vars     = len(spss_names)

    blocks = [
        _header_comment(study_title, csv_filename, seed, n_vars),
        _get_data_block(csv_filename, spss_names),
        _variable_labels_block(variable_dictionary),
        _value_labels_block(variable_dictionary, spss_maps),
        _missing_values_block(variable_dictionary),
        _formats_block(variable_dictionary),
        _variable_level_block(variable_dictionary),
        _section("EXECUTE") + "EXECUTE.\n",
    ]

    filepath.write_text("\n".join(blocks), encoding="utf-8")
    return filepath

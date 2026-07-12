"""
research_engine/exporters/spss_exporter.py
Stage 10 — Export Engine  |  Milestone 1.1.A (SPSS syntax)

Produces a complete SPSS syntax file (.sps) that:
  1. Defines the data file location (GET DATA)
  2. Declares all variable labels (VARIABLE LABELS)
  3. Declares all value labels for categorical variables (VALUE LABELS)
  4. Declares missing value codes (MISSING VALUES)
  5. Sets numeric formats (FORMATS)
  6. Sets measurement level for every variable (VARIABLE LEVEL)
  7. Executes the import (EXECUTE)

Public API
----------
    export_spss_syntax(
        variable_dictionary, spss_maps, output_dir,
        csv_filename, study_title, seed
    ) -> Path
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from research_engine.models.variable import VariableDictionary, MeasurementScale


_MAX_LINE = 76


def _spss_name(name: str) -> str:
    return name.upper().replace(" ", "_")[:64]


def _q(text: str) -> str:
    """Wrap in single quotes, escaping embedded quotes."""
    return "'" + text.replace("'", "''") + "'"


def _section(title: str) -> str:
    bar = "*" + "=" * 70 + "."
    return "\n" + bar + "\n* " + title + "\n" + bar + "\n"


def _wrap_varlist(names: list[str], prefix: str = "  ") -> str:
    """Wrap a variable name list at _MAX_LINE chars."""
    lines, line = [], prefix
    for n in names:
        if len(line) + len(n) + 1 > _MAX_LINE:
            lines.append(line)
            line = "    " + n
        else:
            line += " " + n
    if line.strip():
        lines.append(line)
    return "\n".join(lines)


def _header_comment(study_title: str, csv_filename: str,
                    seed: int, n_vars: int) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "* " + "=" * 70 + ".",
        f"* SPSS Syntax — {study_title}",
        f"* Generated : {now}",
        f"* Seed      : {seed}",
        f"* Variables : {n_vars}",
        f"* Data file : {csv_filename}",
        "*",
        "* INSTRUCTIONS:",
        "*   1. Update the FILE= path below to match your CSV location.",
        "*   2. Open SPSS > File > New > Syntax",
        "*   3. Paste this file and click Run > All",
        "* " + "=" * 70 + ".",
        "",
    ]
    return "\n".join(lines)


def _get_data_block(csv_filename: str, spss_names: list[str]) -> str:
    lines = [
        _section("DATA IMPORT"),
        "GET DATA",
        f"  /TYPE=TXT",
        f"  /FILE={_q(csv_filename)}",
        "  /ENCODING='UTF8'",
        "  /DELIMITERS=','",
        "  /QUALIFIER='\"'",
        "  /ARRANGEMENT=DELIMITED",
        "  /FIRSTCASE=2",
        _wrap_varlist(spss_names, "  /VARIABLES="),
        "  /MAP.",
        "CACHE.",
        "EXECUTE.",
        "",
    ]
    return "\n".join(lines)


def _variable_labels_block(vd: VariableDictionary) -> str:
    lines = [_section("VARIABLE LABELS"), "VARIABLE LABELS"]
    for var in vd:
        sname = _spss_name(var.name)
        label = var.label or var.name.replace("_", " ").title()
        lines.append(f"  {sname:<20} {_q(label)}")
    lines.append("  .")
    return "\n".join(lines) + "\n"


LIKERT_LABELS = (
    "    1 'Strongly Disagree'\n"
    "    2 'Disagree'\n"
    "    3 'Neutral'\n"
    "    4 'Agree'\n"
    "    5 'Strongly Agree'"
)


def _value_labels_block(vd: VariableDictionary,
                         spss_maps: dict) -> str:
    blocks = [_section("VALUE LABELS"), "VALUE LABELS"]

    for var in vd:
        sname = _spss_name(var.name)
        codes: dict = {}

        if var.name in spss_maps:
            codes = {str(lbl): int(code)
                     for lbl, code in spss_maps[var.name].items()}
        elif var.spss_codes:
            codes = {str(lbl): int(code)
                     for lbl, code in var.spss_codes.items()}
        elif (var.scale == MeasurementScale.ORDINAL
              and var.section not in (None, "demographics", "observations")
              and var.allowed_values == [1, 2, 3, 4, 5]):
            blocks.append(f"  /{sname}")
            blocks.append(LIKERT_LABELS)
            continue

        if codes:
            sorted_codes = sorted(codes.items(), key=lambda x: x[1])
            block_lines = [f"  /{sname}"]
            for lbl, code in sorted_codes:
                block_lines.append(f"    {code} {_q(lbl)}")
            blocks.append("\n".join(block_lines))

    blocks.append("  .")
    return "\n".join(blocks) + "\n"


def _missing_values_block(vd: VariableDictionary) -> str:
    lines = [_section("MISSING VALUES")]
    for var in vd:
        sname = _spss_name(var.name)
        code  = "99" if var.scale == MeasurementScale.SCALE else "9"
        lines.append(f"MISSING VALUES {sname} ({code}).")
    return "\n".join(lines) + "\n"


def _formats_block(vd: VariableDictionary) -> str:
    lines = [_section("VARIABLE FORMATS")]
    for var in vd:
        sname = _spss_name(var.name)
        if var.scale == MeasurementScale.SCALE:
            fmt = "F8.2"
        elif (var.scale == MeasurementScale.ORDINAL
              and var.section not in (None, "demographics", "observations")):
            fmt = "F5.2"
        else:
            fmt = "F2.0"
        lines.append(f"FORMATS {sname} ({fmt}).")
    return "\n".join(lines) + "\n"


def _variable_level_block(vd: VariableDictionary) -> str:
    nominal, ordinal, scale = [], [], []
    for var in vd:
        sname = _spss_name(var.name)
        if var.scale == MeasurementScale.NOMINAL:
            nominal.append(sname)
        elif var.scale == MeasurementScale.ORDINAL:
            ordinal.append(sname)
        else:
            scale.append(sname)

    lines = [_section("MEASUREMENT LEVELS")]
    for names, level in [(nominal, "NOMINAL"), (ordinal, "ORDINAL"), (scale, "SCALE")]:
        if names:
            lines.append("VARIABLE LEVEL")
            lines.append(_wrap_varlist(names))
            lines.append(f"  ({level}).")
    return "\n".join(lines) + "\n"


def export_spss_syntax(
    variable_dictionary: VariableDictionary,
    spss_maps:           dict,
    output_dir:          str | Path,
    csv_filename:        str = "data.csv",
    study_title:         str = "Research Study",
    seed:                int = 42,
) -> Path:
    """
    Write a complete SPSS syntax file (.sps).

    Parameters
    ----------
    variable_dictionary : VariableDictionary — all study variables
    spss_maps           : {field: {label: code}} from run.py SPSS_MAPS
    output_dir          : directory to write the .sps file
    csv_filename        : filename of the SPSS CSV (researcher sets full path)
    study_title         : study title (recorded in header comment)
    seed                : random seed (recorded in header comment)

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

    blocks = [
        _header_comment(study_title, csv_filename, seed, len(spss_names)),
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

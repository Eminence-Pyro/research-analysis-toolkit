"""
research_engine/exporters/csv_exporter.py
Stage 10 — Export Engine

Writes Dataset records to CSV files:
  - raw CSV  (labelled values, all variables)
  - SPSS CSV (numeric codes only, SPSS-ready)
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from research_engine.models import Dataset, VariableDictionary


def export_raw(
    dataset:     Dataset,
    output_dir:  str | Path,
    study_title: str = "",
) -> Path:
    """Write a raw CSV with labelled values and return the file path."""
    out  = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = study_title[:25].replace(" ", "_") if study_title else "study"
    path = out / f"{slug}_raw_{ts}.csv"

    records = dataset.to_records()
    if not records:
        path.write_text("")
        return path

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)

    return path


def export_spss(
    dataset:     Dataset,
    output_dir:  str | Path,
    spss_maps:   dict[str, dict[str, int]],
    vd:          VariableDictionary | None = None,
    study_title: str = "",
) -> Path:
    """
    Write a numeric-only SPSS-ready CSV and return the file path.
    Also writes a companion .txt label file listing variable codes.
    """
    out  = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = study_title[:25].replace(" ", "_") if study_title else "study"
    path = out / f"{slug}_spss_{ts}.csv"

    records = dataset.to_records()
    if not records:
        path.write_text("")
        return path

    def encode(row: dict) -> dict:
        out_row: dict = {}
        for k, v in row.items():
            spss_key = k.upper()[:8]
            if k in spss_maps:
                out_row[spss_key] = spss_maps[k].get(str(v), 9)
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                out_row[spss_key] = v
            elif isinstance(v, str) and v in ("Yes", "No"):
                out_row[spss_key] = 1 if v == "Yes" else 0
            else:
                try:
                    out_row[spss_key] = float(v)
                except (ValueError, TypeError):
                    out_row[spss_key] = 9
        return out_row

    encoded = [encode(r) for r in records]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=encoded[0].keys())
        writer.writeheader()
        writer.writerows(encoded)

    # Companion label file
    label_path = out / f"{slug}_spss_labels_{ts}.txt"
    label_lines = ["SPSS Variable Labels\n", "=" * 40 + "\n"]
    if vd:
        for variable in vd:
            short = variable.name.upper()[:8]
            label_lines.append(f"{short:<10} = {variable.label}\n")
            if variable.spss_codes:
                for lbl, code in variable.spss_codes.items():
                    label_lines.append(f"           {code} = {lbl}\n")
    label_path.write_text("".join(label_lines), encoding="utf-8")

    return path

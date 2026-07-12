"""
research_engine/exporters/
Stage 10 — Export Engine

Writes domain objects and analysis results to external file formats.
Nothing in this package generates data or computes statistics.

Public API
----------
    from research_engine.exporters import export_excel, export_raw_csv, export_spss
"""
from research_engine.exporters.excel_exporter import export as export_excel
from research_engine.exporters.csv_exporter   import export_raw as export_raw_csv
from research_engine.exporters.csv_exporter   import export_spss

__all__ = ["export_excel", "export_raw_csv", "export_spss"]

# Word / Chapter Four exporter (Milestone 1.1.A)
from research_engine.exporters.word_exporter import export_word

__all__ = [
    "export_excel", "export_raw_csv", "export_spss", "export_word",
]
from research_engine.exporters.spss_exporter import export_spss_syntax

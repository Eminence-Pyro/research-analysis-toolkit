"""
research_engine/plugins/
v2 Architecture — Plugin System

Plugins extend the toolkit without modifying research_engine/ core.
They register themselves via the PluginRegistry and are discovered
automatically at pipeline startup.

Plugin types
------------
- Exporter plugins    — new output formats (PDF, Word, SPSS syntax, etc.)
- Generator plugins   — new study types (prevalence, KAP, cohort, etc.)
- Analysis plugins    — new statistical methods (regression, Cronbach, ANOVA)
- Parser plugins      — new input formats (Word questionnaire, CSV import)

Usage
-----
    from research_engine.plugins import registry

    # Register a custom exporter
    @registry.exporter("my_format")
    class MyExporter:
        def export(self, dataset, output_dir, **kwargs): ...

    # List registered exporters
    registry.list_exporters()
"""
from research_engine.plugins.registry import PluginRegistry

registry = PluginRegistry()

__all__ = ["registry", "PluginRegistry"]

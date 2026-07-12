# Plugin System

Plugins extend the toolkit without modifying `research_engine/` core.

## Plugin types

| Type | Extends |
|------|---------|
| `exporter` | New output formats (Word, PDF, Google Sheets, ...) |
| `generator` | New study designs (cohort, KAP, prevalence, ...) |
| `analysis` | New statistical methods (ANOVA, regression, Cronbach, ...) |
| `parser` | New input formats (Word .docx questionnaire, CSV import, ...) |

## Registering a plugin

```python
from research_engine.plugins import registry

@registry.exporter("word")
class WordExporter:
    def export(self, dataset, questionnaire, variable_dictionary,
               validation_report, output_dir, **kwargs):
        ...
        return output_path
```

## Using a plugin

```python
from research_engine.plugins import registry
WordExporter = registry.get("exporter", "word")
exporter = WordExporter()
path = exporter.export(dataset, questionnaire, ...)
```

## Listing plugins

```python
registry.list_exporters()   # ['excel', 'csv', 'spss', 'word', ...]
registry.all()              # full dict of all registered plugins
```

## v2 roadmap

Built-in exporters (Excel, CSV, SPSS) will register themselves as plugins in v1.2,
making them interchangeable with community-contributed exporters and enabling
the Pipeline to export to any registered format by name.

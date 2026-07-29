"""
research_engine/plugins/registry.py
Tier 3 — Plugin system for custom generators and exporters

Allows users to register custom data generators, exporters, and
analysis modules without modifying the core engine. Plugins are
discovered from:
  1. Built-in modules in research_engine/generators/, exporters/
  2. User plugins in ~/.rat/plugins/
  3. Any Python module that registers via the decorator API

Public API
----------
    @register_generator("my_study")
    @register_exporter("my_format", extension=".xyz")
    def my_export(dataset, output_path, **kwargs): ...

    list_generators() → list[str]
    list_exporters()  → list[str]
    get_generator(name) → callable
    get_exporter(name)  → callable
    discover_plugins()  → int (count found)
"""
from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


# ══════════════════════════════════════════════════════════════
# Registry
# ══════════════════════════════════════════════════════════════

@dataclass
class PluginInfo:
    """Metadata about a registered plugin."""
    name:        str
    plugin_type: str          # "generator" | "exporter" | "analysis"
    callable:    Callable
    extension:   str          = ""
    description: str          = ""
    version:     str          = "1.0.0"
    author:      str          = ""
    builtin:     bool         = False


class PluginRegistry:
    """Central registry for all plugins."""

    def __init__(self):
        self._generators: dict[str, PluginInfo] = {}
        self._exporters:  dict[str, PluginInfo] = {}
        self._analyses:   dict[str, PluginInfo] = {}
        self._discovered: bool = False

    def register_generator(self, name: str, **meta) -> Callable:
        """Decorator to register a custom data generator."""
        def decorator(func: Callable) -> Callable:
            self._generators[name] = PluginInfo(
                name=name, plugin_type="generator", callable=func, **meta
            )
            return func
        return decorator

    def register_exporter(self, name: str, extension: str = "", **meta) -> Callable:
        """Decorator to register a custom exporter."""
        def decorator(func: Callable) -> Callable:
            self._exporters[name] = PluginInfo(
                name=name, plugin_type="exporter", callable=func,
                extension=extension, **meta
            )
            return func
        return decorator

    def register_analysis(self, name: str, **meta) -> Callable:
        """Decorator to register a custom analysis module."""
        def decorator(func: Callable) -> Callable:
            self._analyses[name] = PluginInfo(
                name=name, plugin_type="analysis", callable=func, **meta
            )
            return func
        return decorator

    def list_generators(self) -> list[str]:
        return sorted(self._generators.keys())

    def list_exporters(self) -> list[str]:
        return sorted(self._exporters.keys())

    def list_analyses(self) -> list[str]:
        return sorted(self._analyses.keys())

    def get_generator(self, name: str) -> Callable:
        info = self._generators.get(name)
        if not info:
            raise KeyError(f"Generator '{name}' not found. Available: {self.list_generators()}")
        return info.callable

    def get_exporter(self, name: str) -> Callable:
        info = self._exporters.get(name)
        if not info:
            raise KeyError(f"Exporter '{name}' not found. Available: {self.list_exporters()}")
        return info.callable

    def get_analysis(self, name: str) -> Callable:
        info = self._analyses.get(name)
        if not info:
            raise KeyError(f"Analysis '{name}' not found. Available: {self.list_analyses()}")
        return info.callable

    def get_exporter_info(self, name: str) -> PluginInfo:
        return self._exporters.get(name)

    def get_generator_info(self, name: str) -> PluginInfo:
        return self._generators.get(name)

    def discover_plugins(self) -> int:
        """
        Discover and load all plugins:
          1. Built-in generators and exporters
          2. User plugins from ~/.rat/plugins/
        """
        if self._discovered:
            return len(self._generators) + len(self._exporters) + len(self._analyses)

        # 1. Load built-in exporters
        self._load_builtin_exporters()

        # 2. Load built-in generators
        self._load_builtin_generators()

        # 3. Load user plugins
        self._load_user_plugins()

        self._discovered = True
        total = len(self._generators) + len(self._exporters) + len(self._analyses)
        return total

    def _load_builtin_exporters(self):
        """Register built-in exporters."""
        try:
            from research_engine.exporters import excel_exporter, pdf_exporter
            self._exporters["excel"] = PluginInfo(
                name="excel", plugin_type="exporter", callable=excel_exporter.export,
                extension=".xlsx", description="Multi-sheet Excel workbook",
                builtin=True
            )
        except Exception:
            pass

        try:
            from research_engine.exporters.pdf_exporter import export_project_pdf
            self._exporters["pdf"] = PluginInfo(
                name="pdf", plugin_type="exporter", callable=export_project_pdf,
                extension=".pdf", description="APA-formatted PDF document",
                builtin=True
            )
        except Exception:
            pass

        try:
            from research_engine.exporters.apa_report import generate_apa_report
            self._exporters["apa"] = PluginInfo(
                name="apa", plugin_type="exporter", callable=generate_apa_report,
                extension=".md", description="APA 7th edition statistical report",
                builtin=True
            )
        except Exception:
            pass

    def _load_builtin_generators(self):
        """Register built-in data generators."""
        try:
            from research_engine.generators import population_generator
            self._generators["population"] = PluginInfo(
                name="population", plugin_type="generator",
                callable=population_generator.generate,
                description="Synthetic population generator",
                builtin=True
            )
        except Exception:
            pass

    def _load_user_plugins(self):
        """Load user plugins from ~/.rat/plugins/ directory."""
        plugin_dir = Path.home() / ".rat" / "plugins"
        if not plugin_dir.exists():
            return

        for py_file in plugin_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(
                    f"rat_plugin_{py_file.stem}", str(py_file)
                )
                module = importlib.util.module_from_spec(spec)
                # Make registry available to the plugin
                sys.modules[spec.name] = module
                spec.loader.exec_module(module)
            except Exception as exc:
                print(f"  ⚠  Failed to load plugin {py_file.name}: {exc}")

    def info(self) -> dict:
        """Return a summary of all registered plugins."""
        return {
            "generators": {n: {"description": p.description, "builtin": p.builtin}
                           for n, p in self._generators.items()},
            "exporters": {n: {"extension": p.extension, "description": p.description, "builtin": p.builtin}
                          for n, p in self._exporters.items()},
            "analyses": {n: {"description": p.description, "builtin": p.builtin}
                         for n, p in self._analyses.items()},
        }


# ══════════════════════════════════════════════════════════════
# Global registry instance
# ══════════════════════════════════════════════════════════════

registry = PluginRegistry()


# Convenience decorators (use these in your plugin files)
def register_generator(name: str, **meta):
    return registry.register_generator(name, **meta)

def register_exporter(name: str, extension: str = "", **meta):
    return registry.register_exporter(name, extension=extension, **meta)

def register_analysis(name: str, **meta):
    return registry.register_analysis(name, **meta)


# ══════════════════════════════════════════════════════════════
# Template for user plugins
# ══════════════════════════════════════════════════════════════

PLUGIN_TEMPLATE = '''"""
Custom plugin for Research Analysis Toolkit
Place this file in ~/.rat/plugins/ and it will be auto-loaded.

Available decorators:
    from research_engine.plugins.registry import register_generator, register_exporter, register_analysis
"""
from research_engine.plugins.registry import register_exporter, register_generator


@register_exporter("my_format", extension=".myf", description="My custom export format")
def my_exporter(dataset, output_path, **kwargs):
    """Export dataset to my custom format."""
    from pathlib import Path
    output_path = Path(output_path)
    output_path.write_text(f"Custom export of {len(dataset)} respondents")
    return output_path
'''

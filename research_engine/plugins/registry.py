"""
research_engine/plugins/registry.py
v2 Architecture — Plugin Registry

Central registry for all plugin types. Plugins are registered by name
and retrieved at runtime. The registry is populated at import time via
decorator syntax or explicit registration.

This is the foundation of the plugin system — no plugins are hardcoded here.
"""
from __future__ import annotations
from typing import Any, Callable, Type


class PluginRegistry:
    """
    Holds all registered plugins by type and name.

    Plugin types: "exporter", "generator", "analysis", "parser"
    """

    def __init__(self) -> None:
        self._plugins: dict[str, dict[str, Any]] = {
            "exporter":  {},
            "generator": {},
            "analysis":  {},
            "parser":    {},
        }

    # ── Registration (decorator syntax) ──────────────────────

    def exporter(self, name: str):
        """Decorator: register a class as an exporter plugin."""
        def decorator(cls):
            self.register("exporter", name, cls)
            return cls
        return decorator

    def generator(self, name: str):
        """Decorator: register a class as a generator plugin."""
        def decorator(cls):
            self.register("generator", name, cls)
            return cls
        return decorator

    def analysis(self, name: str):
        """Decorator: register a class as an analysis plugin."""
        def decorator(cls):
            self.register("analysis", name, cls)
            return cls
        return decorator

    def parser(self, name: str):
        """Decorator: register a class as a parser plugin."""
        def decorator(cls):
            self.register("parser", name, cls)
            return cls
        return decorator

    # ── Explicit registration ─────────────────────────────────

    def register(self, plugin_type: str, name: str, cls: Any) -> None:
        """Register a plugin class by type and name."""
        if plugin_type not in self._plugins:
            raise ValueError(
                f"Unknown plugin type: {plugin_type!r}. "
                f"Valid types: {list(self._plugins.keys())}"
            )
        self._plugins[plugin_type][name] = cls

    # ── Retrieval ─────────────────────────────────────────────

    def get(self, plugin_type: str, name: str) -> Any:
        """Retrieve a plugin class by type and name."""
        plugins = self._plugins.get(plugin_type, {})
        if name not in plugins:
            raise KeyError(
                f"No {plugin_type} plugin named {name!r}. "
                f"Available: {list(plugins.keys())}"
            )
        return plugins[name]

    def list_exporters(self)  -> list[str]: return list(self._plugins["exporter"])
    def list_generators(self) -> list[str]: return list(self._plugins["generator"])
    def list_analysis(self)   -> list[str]: return list(self._plugins["analysis"])
    def list_parsers(self)    -> list[str]: return list(self._plugins["parser"])

    def all(self) -> dict[str, dict[str, Any]]:
        """Return a snapshot of all registered plugins."""
        return {k: dict(v) for k, v in self._plugins.items()}

    def __repr__(self) -> str:
        counts = {k: len(v) for k, v in self._plugins.items()}
        return f"PluginRegistry({counts})"

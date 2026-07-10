"""
rdg/utils/console.py — pretty terminal output helpers.
Falls back gracefully if 'rich' is not installed.
"""
from __future__ import annotations
from pathlib import Path

try:
    from rich.console import Console
    from rich.rule    import Rule
    from rich.text    import Text
    _RICH = True
    _con  = Console()
except ImportError:
    _RICH = False


def banner(title: str, subtitle: str = "") -> None:
    sep = "─" * 58
    print(f"\n{sep}")
    if _RICH:
        _con.print(f"  [bold yellow]{title}[/bold yellow]")
        if subtitle:
            _con.print(f"  [dim]{subtitle}[/dim]")
    else:
        print(f"  {title}")
        if subtitle:
            print(f"  {subtitle}")
    print(sep)


def step(n: int, total: int, label: str) -> None:
    if _RICH:
        _con.print(f"\n  [bold cyan]Step {n}/{total}[/bold cyan]  {label}")
    else:
        print(f"\n  [{n}/{total}] {label}")


def done(paths: dict[str, Path]) -> None:
    print()
    if _RICH:
        _con.print("  [bold green]✓ Complete — outputs written:[/bold green]")
    else:
        print("  ✓ Complete — outputs written:")
    for label, p in paths.items():
        print(f"    {label:<10} → {p.name}")
    print()

from __future__ import annotations

from pathlib import Path

import typer
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from zenve_engine.config import ConfigError, load_project_settings
from zenve_engine.pipeline import validate_pipeline

console = Console()


def cmd(repo_root: Path = Path(".")) -> None:
    """Display and validate the pipeline from `.zenve/settings.json`."""
    try:
        settings = load_project_settings(repo_root)
    except ConfigError as exc:
        console.print(f"[red]✗[/red] {exc}", highlight=False)
        raise typer.Exit(1) from exc

    if not settings.pipeline:
        console.print()
        console.print("  [dim]No pipeline defined.[/dim]")
        console.print()
        return

    report = validate_pipeline(settings.pipeline)
    bad_refs = {src for src, _ in report.unknown_refs}
    cycle_nodes = {node for cyc in report.cycles for node in cyc}

    table = Table(
        box=box.ROUNDED,
        border_style="dim",
        header_style="bold cyan",
        show_lines=False,
        pad_edge=True,
    )
    table.add_column("LABEL", style="cyan", no_wrap=True)
    table.add_column("NEXT", no_wrap=True)

    for src, dst in settings.pipeline.items():
        if dst is None:
            next_cell = Text("→ end", style="dim")
        elif src in bad_refs:
            next_cell = Text(f"→ {dst}  ⚠ unknown ref", style="red")
        elif src in cycle_nodes:
            next_cell = Text(f"→ {dst}  ⚠ cycle", style="yellow")
        else:
            next_cell = Text(f"→ {dst}")

        table.add_row(src, next_cell)

    console.print()
    console.print(table)
    console.print()

    if report.unknown_refs:
        for src, dst in report.unknown_refs:
            console.print(f"  [red]⚠[/red] [bold]{src}[/bold] → [bold]{dst}[/bold] is not a pipeline key", highlight=False)
        console.print()
    if report.cycles:
        for cyc in report.cycles:
            console.print(f"  [yellow]⚠[/yellow] cycle: {' → '.join(cyc)}", highlight=False)
        console.print()
    if report.ok:
        console.print(f"  [green]✓[/green] pipeline is valid")
        console.print()

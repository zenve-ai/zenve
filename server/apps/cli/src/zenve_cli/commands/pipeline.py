from __future__ import annotations

from pathlib import Path

import typer

from zenve_cli.core.config import ConfigError, load_project_settings
from zenve_cli.core.pipeline import validate_pipeline


def cmd(repo_root: Path = Path(".")) -> None:
    """Display and validate the pipeline from `.zenve/settings.json`."""
    try:
        settings = load_project_settings(repo_root)
    except ConfigError as exc:
        typer.echo(f"✗ {exc}")
        raise typer.Exit(1) from exc

    if not settings.pipeline:
        typer.echo("No pipeline defined.")
        return

    typer.echo("Pipeline:")
    for src, dst in settings.pipeline.items():
        arrow = "·" if dst is None else f"→ {dst}"
        typer.echo(f"  {src}  {arrow}")

    report = validate_pipeline(settings.pipeline)
    if report.unknown_refs:
        typer.echo("")
        typer.echo("⚠ Unknown label refs:")
        for src, dst in report.unknown_refs:
            typer.echo(f"  {src} → {dst} (not a pipeline key)")
    if report.cycles:
        typer.echo("")
        typer.echo("⚠ Cycles detected:")
        for cyc in report.cycles:
            typer.echo(f"  {' → '.join(cyc)}")
    if report.ok:
        typer.echo("")
        typer.echo("✓ pipeline is valid")

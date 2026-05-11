from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from zenve_cli.console import ZenveTUI
from zenve_cli.runtime.client import report_error, runtime_request

console = Console()


def resolve_workspace_id(repo_root: Path) -> str:
    abs_path = str(repo_root.expanduser().resolve())
    resp = runtime_request("GET", "/api/v1/workspaces")
    if resp.status_code != 200:
        report_error(resp)
        raise typer.Exit(1)
    for w in resp.json():
        if w["path"] == abs_path:
            return w["id"]
    console.print(f"[red]✗[/red] No workspace registered at [cyan]{abs_path}[/cyan]")
    console.print("  Register it with: [cyan]zenve workspace add .[/cyan]")
    raise typer.Exit(1)


def resolve_run_id(workspace_id: str, run_id: str | None) -> str:
    if run_id:
        return run_id
    resp = runtime_request("GET", f"/api/v1/workspaces/{workspace_id}/runs/active-run")
    if resp.status_code == 200:
        return resp.json()["run_id"]
    if resp.status_code != 404:
        report_error(resp)
        raise typer.Exit(1)
    # No active run — fall back to latest
    resp = runtime_request("GET", f"/api/v1/workspaces/{workspace_id}/runs/latest")
    if resp.status_code != 200:
        report_error(resp)
        raise typer.Exit(1)
    latest = resp.json()
    if latest is None:
        console.print("[yellow]◆[/yellow] No runs found for this workspace.")
        raise typer.Exit(0)
    return latest["run_id"]


def cmd(repo_root: Path, run_id: str | None) -> None:
    workspace_id = resolve_workspace_id(repo_root)
    resolved_run_id = resolve_run_id(workspace_id, run_id)

    resp = runtime_request("GET", f"/api/v1/workspaces/{workspace_id}/runs/{resolved_run_id}/events")
    if resp.status_code != 200:
        report_error(resp)
        raise typer.Exit(1)

    events = resp.json()
    if not events:
        console.print(f"[yellow]◆[/yellow] No events found for run [cyan]{resolved_run_id}[/cyan]")
        raise typer.Exit(0)

    ZenveTUI(events=events).run()

from __future__ import annotations

import shutil
from pathlib import Path

import httpx
import questionary
import typer
from rich import box
from rich.console import Console
from rich.table import Table

from zenve_cli.commands.ui import WIZARD_STYLE
from zenve_cli.runtime.client import ensure_runtime, report_error, runtime_request, runtime_url
from zenve_engine.constants import ZENVE_DIR

workspace_app = typer.Typer(help="Workspace management commands")
console = Console()


def looks_like_path(target: str) -> bool:
    return "/" in target or "." in target or target == "" or Path(target).exists()


def resolve_workspace(target: str) -> dict:
    """Find a registered workspace by id or path. Exits with error if not found."""
    resp = runtime_request("GET", "/api/v1/workspaces")
    if resp.status_code != 200:
        report_error(resp)
        raise typer.Exit(1)
    workspaces = resp.json()

    if looks_like_path(target):
        abs_path = str(Path(target).expanduser().resolve())
        for w in workspaces:
            if w["path"] == abs_path:
                return w
        console.print(f"[red]✗[/red] No workspace registered at [cyan]{abs_path}[/cyan]")
        raise typer.Exit(1)

    for w in workspaces:
        if w["id"] == target:
            return w
    console.print(f"[red]✗[/red] No workspace with id [cyan]{target}[/cyan]")
    raise typer.Exit(1)


def register_path(path: Path) -> tuple[int, dict | None]:
    """POST a workspace path to the runtime. Returns (status_code, body_or_none)."""
    abs_path = path.expanduser().resolve()
    resp = runtime_request("POST", "/api/v1/workspaces", json={"path": str(abs_path)})
    try:
        body = resp.json()
    except Exception:
        body = None
    return resp.status_code, body


@workspace_app.command("init")
def init_workspace(
    path: Path = typer.Argument(Path("."), help="Path to the repo root"),
    description: str | None = typer.Option(None, "--description", help="Project description"),
) -> None:
    """Scaffold .zenve/ interactively and register it with the local runtime."""
    from zenve_cli.commands import init as init_cmd

    init_cmd.cmd(repo_root=path, description=description)


@workspace_app.command("add")
def add_workspace(
    path: Path = typer.Argument(Path("."), help="Path to a repo with a .zenve/ folder"),
) -> None:
    """Register a workspace with the local runtime."""
    ensure_runtime()
    status, body = register_path(path)
    if status == 201 and body:
        console.print(f"[green]✓[/green] Registered [cyan]{body['path']}[/cyan] (id: {body['id']})")
        return
    if status == 409:
        console.print(f"[yellow]◆[/yellow] Already registered: {body.get('detail') if body else ''}")
        return
    console.print(f"[red]✗[/red] {status}: {body.get('detail') if body else ''}")
    raise typer.Exit(1)


@workspace_app.command("ls")
def list_workspaces() -> None:
    """List workspaces registered with the runtime."""
    ensure_runtime()
    resp = runtime_request("GET", "/api/v1/workspaces")
    if resp.status_code != 200:
        report_error(resp)
        raise typer.Exit(1)
    workspaces = resp.json()
    if not workspaces:
        console.print("[dim]No workspaces registered.[/dim]")
        return

    table = Table(
        box=box.ROUNDED,
        border_style="dim",
        header_style="bold cyan",
        show_lines=False,
        pad_edge=True,
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("PATH")
    table.add_column("REGISTERED", style="dim")

    for w in workspaces:
        registered = w["registered_at"].replace("T", " ").replace("Z", "")
        table.add_row(w["id"], w["path"], registered)

    console.print()
    console.print(table)
    console.print()


@workspace_app.command("remove")
def remove_workspace(
    target: str = typer.Argument(..., help="Workspace id or path (e.g. '.')"),
) -> None:
    """Unregister a workspace from the runtime (does not touch .zenve/)."""
    ensure_runtime()
    workspace = resolve_workspace(target)
    resp = runtime_request("DELETE", f"/api/v1/workspaces/{workspace['id']}")
    if resp.status_code == 204:
        console.print(f"[green]✓[/green] Unregistered [cyan]{workspace['path']}[/cyan]")
        return
    report_error(resp)
    raise typer.Exit(1)


@workspace_app.command("clean")
def clean_workspace(
    path: Path = typer.Argument(Path("."), help="Path to the repo root"),
) -> None:
    """Deregister and delete .zenve/ — removes Zenve from this repo."""
    abs_path = path.expanduser().resolve()
    zenve_path = abs_path / ZENVE_DIR
    if not zenve_path.exists():
        console.print(f"[red]✗[/red] No [cyan].zenve/[/cyan] found at {abs_path}")
        raise typer.Exit(1)

    matched: dict | None = None
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{runtime_url()}/api/v1/workspaces")
        if resp.status_code == 200:
            for w in resp.json():
                if w["path"] == str(abs_path):
                    matched = w
                    break
    except httpx.ConnectError:
        console.print(
            f"[yellow]◆[/yellow] Runtime not reachable at [cyan]{runtime_url()}[/cyan] — "
            "skipping deregister"
        )

    confirmed = questionary.confirm(
        f"Delete {zenve_path} and deregister this workspace?",
        default=False,
        style=WIZARD_STYLE,
        qmark="◆",
    ).ask()
    if not confirmed:
        console.print("[dim]Aborted.[/dim]")
        raise typer.Exit(0)

    if matched is not None:
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.delete(f"{runtime_url()}/api/v1/workspaces/{matched['id']}")
            if resp.status_code == 204:
                console.print(f"[green]✓[/green] Deregistered (id: {matched['id']})")
            else:
                report_error(resp)
        except httpx.ConnectError:
            console.print("[yellow]◆[/yellow] Runtime went away — skipping deregister")

    shutil.rmtree(zenve_path)
    console.print(f"[green]✓[/green] Removed [cyan]{zenve_path}[/cyan]")
    console.print(
        "[dim]Commit the deletion with: git add -A .zenve && git commit -m 'remove zenve'[/dim]"
    )

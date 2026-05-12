from __future__ import annotations

import base64
from pathlib import Path

import questionary
import typer
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from zenve_cli.commands.ui import WIZARD_STYLE, sep
from zenve_cli.models.errors import ZenveError
from zenve_cli.models.github_template import SkillSummary
from zenve_cli.runtime.client import ensure_runtime, report_error, runtime_request
from zenve_cli.services.scaffolding import ScaffoldingService

skill_app = typer.Typer(help="Skill management commands")
console = Console()


def installed_skill_names(repo_root: Path) -> set[str]:
    d = repo_root / ".agents" / "skills"
    if not d.exists():
        return set()
    return {p.name for p in d.iterdir() if p.is_dir() and not p.name.startswith(".")}


def fetch_skills() -> list[SkillSummary]:
    """Fetch skill list from the runtime."""
    ensure_runtime()
    resp = runtime_request("GET", "/api/v1/skills")
    if resp.status_code != 200:
        report_error(resp)
        raise typer.Exit(1)
    return [SkillSummary(**s) for s in resp.json()]


def fetch_skill_files(skill_id: str) -> dict[str, bytes]:
    """Fetch and decode skill files from runtime."""
    resp = runtime_request("GET", f"/api/v1/skills/{skill_id}/files")
    if resp.status_code != 200:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise ZenveError(f"HTTP {resp.status_code}: {detail}")
    data = resp.json()
    return {k: base64.b64decode(v) for k, v in data["files"].items()}


def collect_skills_wizard(
    skills: list[SkillSummary],
    installed: set[str] | None = None,
) -> list[str]:
    """Interactive checkbox to pick skills. Returns selected skill IDs."""
    installed = installed or set()
    choices = []
    for s in skills:
        if s.id in installed:
            choices.append(questionary.Choice(title=s.id, value=s.id, disabled="installed"))
        else:
            choices.append(questionary.Choice(title=s.id, value=s.id))

    available = [c for c in choices if not getattr(c, "disabled", None)]
    if not available:
        return []

    selected = questionary.checkbox(
        "Select skills to install",
        choices=choices,
        style=WIZARD_STYLE,
        qmark="◆",
        instruction="(space to toggle, enter to confirm)",
    ).ask()

    return selected or []


def install_skills(
    repo_root: Path,
    skill_files: dict[str, dict[str, bytes]],
) -> list[str]:
    """Write pre-fetched skill files to disk. Returns installed skill IDs."""
    scaffold = ScaffoldingService()
    installed_now: list[str] = []
    for skill_id, files in skill_files.items():
        scaffold.write_skill_files(repo_root, skill_id, files)
        installed_now.append(skill_id)
        console.print(f"[dim]│[/dim]  [green]✓[/green] {skill_id}")
    return installed_now


def fetch_and_install_skills(
    repo_root: Path,
    selected_ids: list[str],
) -> list[str]:
    """Fetch files from runtime and install. Returns installed skill IDs."""
    scaffold = ScaffoldingService()
    installed_now: list[str] = []
    for skill_id in selected_ids:
        try:
            files = fetch_skill_files(skill_id)
        except ZenveError as exc:
            console.print(
                f"[dim]│[/dim]  [yellow]⚠[/yellow] {skill_id} — {exc.message}"
            )
            continue
        scaffold.write_skill_files(repo_root, skill_id, files)
        installed_now.append(skill_id)
        console.print(f"[dim]│[/dim]  [green]✓[/green] {skill_id}")
    return installed_now


@skill_app.command("ls")
def list_skills(
    repo_root: Path = typer.Option(Path("."), "--repo"),
) -> None:
    """List available skills from the remote repo."""
    try:
        skills = fetch_skills()
    except SystemExit:
        raise
    except Exception as exc:
        console.print(f"[red]✗[/red] Could not fetch skills: {exc}", highlight=False)
        raise typer.Exit(1)  # noqa: B904

    if not skills:
        console.print()
        console.print("  [dim]No skills found.[/dim]")
        console.print()
        return

    installed = installed_skill_names(repo_root)

    table = Table(
        box=box.ROUNDED,
        border_style="dim",
        header_style="bold cyan",
        show_lines=False,
        pad_edge=True,
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("NAME", no_wrap=True)
    table.add_column("STATUS", justify="center")

    for skill in skills:
        is_installed = skill.id in installed
        if is_installed:
            table.add_row(skill.id, skill.name, Text("● installed", style="green"))
        else:
            table.add_row(
                Text(skill.id, style="dim cyan"),
                Text(skill.name, style="dim"),
                Text(""),
            )

    console.print()
    console.print(table)
    console.print()


@skill_app.command("show")
def show_skill(
    skill_id: str = typer.Argument(..., help="Skill ID to show details for"),
    repo_root: Path = typer.Option(Path("."), "--repo"),
) -> None:
    """Show details for a specific skill."""
    try:
        skills = fetch_skills()
    except SystemExit:
        raise
    except Exception as exc:
        console.print(f"[red]✗[/red] Could not fetch skills: {exc}", highlight=False)
        raise typer.Exit(1)  # noqa: B904

    skill = next((s for s in skills if s.id == skill_id), None)
    if skill is None:
        console.print(f"[red]✗[/red] Skill [bold]{skill_id}[/bold] not found.", highlight=False)
        raise typer.Exit(1)  # noqa: B904

    installed = skill.id in installed_skill_names(repo_root)

    console.print()
    console.print(f"  [bold cyan]◆[/bold cyan] [bold]{skill.name}[/bold]")
    console.print()
    console.print(f"  [dim]ID[/dim]           {skill.id}")
    console.print(f"  [dim]NAME[/dim]         {skill.name}")
    console.print(f"  [dim]DESCRIPTION[/dim]  {skill.description or '—'}")
    status_text = Text("● installed", style="green") if installed else Text("○ not installed", style="dim")
    console.print(f"  [dim]STATUS[/dim]       ", end="")
    console.print(status_text)
    console.print()


@skill_app.command("add")
def add_skills(
    repo_root: Path = typer.Option(Path("."), "--repo"),
) -> None:
    """Install skills into .agents/skills/ and link .claude/skills/."""
    try:
        skills = fetch_skills()
    except SystemExit:
        raise
    except Exception as exc:
        console.print(f"[red]✗[/red] Could not fetch skills: {exc}", highlight=False)
        raise typer.Exit(1)  # noqa: B904

    if not skills:
        console.print("[red]✗[/red] No skills found.", highlight=False)
        raise typer.Exit(1)  # noqa: B904

    selected_ids = collect_skills_wizard(skills, installed_skill_names(repo_root))
    sep()

    if not selected_ids:
        console.print("[dim]No skills selected.[/dim]")
        raise typer.Exit(0)

    console.print("[cyan]◆[/cyan] Installing skills...")
    sep()

    installed_now = fetch_and_install_skills(repo_root, selected_ids)

    sep()
    console.print(
        f"[cyan]◆[/cyan] Installed {len(installed_now)} skill(s): {', '.join(installed_now)}"
    )
    console.print()

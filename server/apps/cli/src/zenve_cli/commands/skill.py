from __future__ import annotations

from pathlib import Path

import questionary
import typer
from rich.console import Console
from rich.text import Text

from zenve_cli.commands.snapshot import resolve_github_token
from zenve_cli.commands.ui import WIZARD_STYLE, sep
from zenve_cli.constants import DEFAULT_SKILLS_REPO
from zenve_config.settings import get_settings
from zenve_models.errors import ZenveError
from zenve_models.github_template import SkillSummary
from zenve_services.scaffolding import ScaffoldingService
from zenve_services.template import GitHubTemplateService

skill_app = typer.Typer(help="Skill management commands")
console = Console()


def installed_skill_names(repo_root: Path) -> set[str]:
    d = repo_root / ".agents" / "skills"
    if not d.exists():
        return set()
    return {p.name for p in d.iterdir() if p.is_dir() and not p.name.startswith(".")}


def make_skill_svc() -> GitHubTemplateService:
    settings = get_settings().model_copy(
        update={
            "github_agents_repo": DEFAULT_SKILLS_REPO,
            "github_token": get_settings().github_token or resolve_github_token(),
        }
    )
    return GitHubTemplateService(settings)


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
    selected_ids: list[str],
    svc: GitHubTemplateService,
) -> list[str]:
    """Download skills and create .claude/skills/ symlinks. Returns installed IDs."""
    scaffold = ScaffoldingService()
    installed_now: list[str] = []
    for skill_id in selected_ids:
        try:
            files = svc.fetch_skill_files(skill_id)
        except ZenveError as exc:
            console.print(
                f"[dim]│[/dim]  [yellow]⚠[/yellow] [white]{skill_id}[/white] — {exc.message}"
            )
            continue
        scaffold.write_skill_files(repo_root, skill_id, files)
        installed_now.append(skill_id)
        console.print(f"[dim]│[/dim]  [green]✓[/green] [white]{skill_id}[/white]")
    return installed_now


@skill_app.command("list")
def list_skills(
    repo_root: Path = typer.Option(Path("."), "--repo"),
) -> None:
    """List available skills from the remote repo."""
    svc = make_skill_svc()
    try:
        skills = svc.list_skills()
    except ZenveError as exc:
        console.print(f"[red]✗[/red] Could not fetch skills: {exc.message}", highlight=False)
        raise typer.Exit(1)  # noqa: B904

    if not skills:
        console.print("[dim]No skills found.[/dim]")
        return

    installed = installed_skill_names(repo_root)
    console.print()
    for skill in skills:
        line = Text()
        line.append("  ◆ ", style="bold cyan")
        line.append(skill.id, style="bold white")
        if skill.id in installed:
            line.append("  installed", style="dim green")
        console.print(line)
        if skill.description:
            console.print(f"    [dim]{skill.description}[/dim]")
        console.print()


@skill_app.command("add")
def add_skills(
    repo_root: Path = typer.Option(Path("."), "--repo"),
) -> None:
    """Install skills into .agents/skills/ and link .claude/skills/."""
    svc = make_skill_svc()
    try:
        skills = svc.list_skills()
    except ZenveError as exc:
        console.print(f"[red]✗[/red] Could not fetch skills: {exc.message}", highlight=False)
        raise typer.Exit(1)  # noqa: B904

    if not skills:
        console.print("[red]✗[/red] No skills found.", highlight=False)
        raise typer.Exit(1)  # noqa: B904

    selected_ids = collect_skills_wizard(skills, installed_skill_names(repo_root))
    sep()

    if not selected_ids:
        console.print("[dim]No skills selected.[/dim]")
        raise typer.Exit(0)

    console.print("[cyan]◆[/cyan] [white]Installing skills...[/white]")
    sep()

    installed_now = install_skills(repo_root, selected_ids, svc)

    sep()
    console.print(
        f"[cyan]◆[/cyan] [white]Installed {len(installed_now)} skill(s): {', '.join(installed_now)}[/white]"
    )
    console.print()

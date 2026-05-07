from __future__ import annotations

import json
from pathlib import Path

import questionary
import typer
from rich.console import Console
from rich.text import Text

from zenve_cli.commands.snapshot import resolve_github_token
from zenve_cli.commands.ui import WIZARD_STYLE, sep
from zenve_cli.constants import DEFAULT_AGENTS_PATH, DEFAULT_REGISTRY_REPO
from zenve_cli.core.config import zenve_dir
from zenve_cli.core.discovery import AGENTS_SUBDIR, discover_agents
from zenve_cli.models.settings import AgentSettings
from zenve_cli.runtime.commit import GitError, commit_zenve_dir
from zenve_config.settings import get_settings
from zenve_models.errors import ZenveError
from zenve_services.agent import build_agent_files
from zenve_services.agent_lock import AgentLockService
from zenve_services.scaffolding import ScaffoldingService
from zenve_services.template import GitHubTemplateService
from zenve_utils.scaffolding import slugify

agent_app = typer.Typer(help="Agent management commands")
console = Console()


def _make_template_service() -> GitHubTemplateService:
    settings = get_settings().model_copy(
        update={
            "github_agents_repo": get_settings().github_agents_repo or DEFAULT_REGISTRY_REPO,
            "github_token": get_settings().github_token or resolve_github_token(),
        }
    )
    return GitHubTemplateService(settings, base_path=DEFAULT_AGENTS_PATH)


def _resolve_template_slug(t) -> str:
    return t.slug or slugify(t.name if getattr(t, "name", None) else t.id)


def _do_commit(repo_root: Path, message: str, branch: str) -> None:
    try:
        committed = commit_zenve_dir(repo_root, message, branch=branch)
        if committed:
            console.print(
                "[cyan]◆[/cyan] [white]Committed and pushed [cyan].zenve/[/cyan][/white]"
            )
        else:
            console.print("[yellow]◆[/yellow] [white]Nothing to commit[/white]")
    except GitError as exc:
        console.print(f"[red]✗[/red] Git error: {exc}")


def iter_agent_dirs(repo_root: Path) -> list[Path]:
    adir = zenve_dir(repo_root) / AGENTS_SUBDIR
    if not adir.exists():
        return []
    return sorted(d for d in adir.iterdir() if d.is_dir() and not d.name.startswith("."))


def load_agent_settings(path: Path) -> AgentSettings | None:
    settings_path = path / "settings.json"
    if not settings_path.exists():
        return None
    raw = json.loads(settings_path.read_text(encoding="utf-8"))
    return AgentSettings.model_validate(raw)


def save_agent_settings(path: Path, settings: AgentSettings) -> None:
    settings_path = path / "settings.json"
    settings_path.write_text(settings.model_dump_json(indent=2), encoding="utf-8")


def set_enabled(repo_root: Path, name: str, enabled: bool) -> None:
    agents = discover_agents(repo_root)
    path: Path | None = None
    for a in agents:
        if a.name == name:
            path = a.path
            break
    if path is None:
        path = zenve_dir(repo_root) / AGENTS_SUBDIR / name
        if not (path / "settings.json").exists():
            typer.echo(f"✗ Agent not found: {name!r}")
            raise typer.Exit(1)

    settings = load_agent_settings(path)
    if settings is None:
        typer.echo(f"✗ Could not load settings for {name!r}")
        raise typer.Exit(1)
    updated = settings.model_copy(update={"enabled": enabled})
    save_agent_settings(path, updated)


def collect_agents_wizard(
    templates: list, existing_slugs: set[str] | None = None
) -> list[tuple[str, str | None]]:
    """Collect agent specs via checkbox."""
    from questionary import Choice

    existing_slugs = existing_slugs or set()
    choices = []
    for t in templates:
        agent_slug = t.slug or slugify(t.name if hasattr(t, "name") and t.name else t.id)
        if agent_slug in existing_slugs:
            choices.append(Choice(title=t.id, value=t.id, disabled="installed"))
        else:
            choices.append(Choice(title=t.id, value=t.id))

    available = [c for c in choices if not getattr(c, "disabled", None)]
    if not available:
        return []

    selected_ids = questionary.checkbox(
        "Select agents to install",
        choices=choices,
        style=WIZARD_STYLE,
        qmark="◆",
        instruction="(space to toggle, enter to confirm)",
    ).ask()

    if selected_ids is None:
        raise typer.Exit(1)

    agents: list[tuple[str, str | None]] = []
    for template_id in selected_ids:
        tmpl = next((t for t in templates if t.id == template_id), None)
        name = tmpl.name if tmpl else template_id
        agents.append((name, template_id))

    return agents


@agent_app.command("list")
def list_agents(repo_root: Path = typer.Option(Path("."), "--repo")) -> None:
    """List all agents and their enabled/disabled status."""
    dirs = iter_agent_dirs(repo_root)
    if not dirs:
        console.print("[dim]No agents found.[/dim]")
        return

    console.print()
    for d in dirs:
        s = load_agent_settings(d)

        # Slug header
        slug_line = Text()
        slug_line.append("  ◆ ", style="bold cyan")
        slug_line.append(d.name, style="bold white")
        console.print(slug_line)

        if s is None:
            console.print("    [dim red]missing settings.json[/dim red]")
            console.print()
            continue

        label_w = 12

        def row(label: str, value: str, value_style: str = "white", _w: int = label_w) -> None:
            line = Text()
            line.append(f"    {label:<{_w}}", style="dim")
            line.append(value, style=value_style)
            console.print(line)

        row("slug", s.slug)
        row("name", s.name)

        if s.enabled:
            row("status", "● enabled", "bold green")
        else:
            row("status", "○ disabled", "dim red")

        row("picks up", s.picks_up, "yellow")
        row("label", s.github_label, "cyan")
        row("model", str(s.adapter_config.get("model", "")), "dim white")

        console.print()


@agent_app.command("logs")
def logs(name: str, repo_root: Path = typer.Option(Path("."), "--repo")) -> None:
    """Show run history for a specific agent."""
    agent_dir = zenve_dir(repo_root) / AGENTS_SUBDIR / name
    runs_dir = agent_dir / "runs"
    if not runs_dir.exists():
        typer.echo(f"No runs for agent {name!r}.")
        return
    files = sorted(runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        typer.echo(f"No runs for agent {name!r}.")
        return
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        typer.echo(
            f"  {data.get('run_id', '?'):<24} {data.get('status', '?'):<10} "
            f"{data.get('finished_at', '?')}"
        )


@agent_app.command("enable")
def enable(name: str, repo_root: Path = typer.Option(Path("."), "--repo")) -> None:
    """Enable a disabled agent."""
    set_enabled(repo_root, name, True)
    typer.echo(f"✓ Enabled agent {name!r}")


@agent_app.command("disable")
def disable(name: str, repo_root: Path = typer.Option(Path("."), "--repo")) -> None:
    """Disable an agent without removing it."""
    set_enabled(repo_root, name, False)
    typer.echo(f"✓ Disabled agent {name!r}")


@agent_app.command("add")
def add(
    repo_root: Path = typer.Option(Path("."), "--repo"),
    agent: str | None = typer.Option(
        None, "--agent", help="Install a specific template by slug (skips wizard)"
    ),
) -> None:
    """Add new agents to an already-initialized project."""
    zdir = zenve_dir(repo_root)
    if not zdir.exists():
        console.print(
            "[red]✗[/red] No [cyan].zenve/[/cyan] directory found. Run [bold]zenve init[/bold] first."
        )
        raise typer.Exit(1)

    try:
        existing_settings: dict = json.loads((zdir / "settings.json").read_bytes())
    except Exception:
        existing_settings = {}
    existing_pipeline: dict = existing_settings.get("pipeline", {})

    agents_dir = zdir / "agents"
    existing_agent_slugs: set[str] = set()
    if agents_dir.exists():
        existing_agent_slugs = {p.name for p in agents_dir.iterdir() if p.is_dir()}

    svc = _make_template_service()

    try:
        templates = svc.list_templates()
    except ZenveError as exc:
        console.print(
            f"[red]✗[/red] Could not fetch agent templates: {exc.message}", highlight=False
        )
        raise typer.Exit(1)  # noqa: B904

    if not templates:
        console.print("[red]✗[/red] No agent templates found.", highlight=False)
        raise typer.Exit(1)

    # --agent SLUG: non-interactive single install
    if agent is not None:
        match = next(
            (t for t in templates if t.id == agent or _resolve_template_slug(t) == agent),
            None,
        )
        if match is None:
            console.print(
                f"[red]✗[/red] No template found for slug [bold]{agent}[/bold]."
            )
            raise typer.Exit(1)
        target_slug = _resolve_template_slug(match)
        if target_slug in existing_agent_slugs:
            console.print(
                f"[yellow]◆[/yellow] Agent [bold]{target_slug}[/bold] is already installed. "
                f"Use [bold]zenve agents update --agent {target_slug}[/bold] to re-fetch."
            )
            raise typer.Exit(0)
        agent_specs = [(match.name if getattr(match, "name", None) else match.id, match.id)]
    else:
        available_templates = [
            t for t in templates if _resolve_template_slug(t) not in existing_agent_slugs
        ]
        if not available_templates:
            console.print(
                "[dim]All available agents are already installed. "
                "Use [bold]zenve agents update[/bold] to re-fetch.[/dim]"
            )
            raise typer.Exit(0)

        agent_specs = collect_agents_wizard(templates, existing_slugs=existing_agent_slugs)
        sep()
        if not agent_specs:
            console.print("[dim]No agents selected.[/dim]")
            raise typer.Exit(0)

    # Scaffold + record lock
    console.print("[cyan]◆[/cyan] [white]Scaffolding agent files...[/white]")
    sep()

    scaffold = ScaffoldingService()
    lock = AgentLockService(zdir)
    commit_sha = svc.get_head_sha()
    source = svc.repo or DEFAULT_REGISTRY_REPO
    pipeline: dict[str, None] = {}

    for agent_name, template_id in agent_specs:
        try:
            agent_slug, files = build_agent_files(agent_name, template_id, svc)
        except ZenveError as exc:
            console.print(
                f"[yellow]Warning:[/yellow] could not fetch template '{template_id}': {exc.message}"
            )
            agent_slug, files = build_agent_files(agent_name, None, svc)
            template_id = None
        pipeline[f"zenve:{agent_slug}"] = None
        scaffold.write_agent_files(zdir, agent_slug, files)
        if template_id is not None:
            lock.record_install(
                slug=agent_slug,
                template_id=template_id,
                files=files,
                source=source,
                commit_sha=commit_sha,
            )
        console.print(f"  [green]✓[/green] [white]{agent_slug}[/white]")

    scaffold.update_pipeline(zdir, pipeline)

    added_slugs = list(pipeline.keys() - set(existing_pipeline.keys()))
    sep()
    console.print(
        f"[cyan]◆[/cyan] [white]Added {len(added_slugs)} agent(s): "
        f"{', '.join(added_slugs)}[/white]"
    )
    sep()

    do_commit = questionary.confirm(
        "Commit and push .zenve/?",
        default=True,
        style=WIZARD_STYLE,
        qmark="◆",
    ).ask()
    sep()

    if do_commit:
        branch = existing_settings.get("default_branch", "main")
        _do_commit(
            repo_root,
            f"[zenve] add {len(added_slugs)} agent(s): {', '.join(added_slugs)}",
            branch=branch,
        )
    else:
        console.print(
            "[cyan]◆[/cyan] [white]Commit and push [cyan].zenve/[/cyan] to activate[/white]"
        )
    console.print()


_STATUS_LABEL = {
    "clean": ("clean", "dim green"),
    "modified": ("modified", "yellow"),
    "unknown": ("not in lock", "magenta"),
    "missing": ("missing", "red"),
}


@agent_app.command("update")
def update(
    repo_root: Path = typer.Option(Path("."), "--repo"),
    agent: str | None = typer.Option(
        None, "--agent", help="Update a specific agent by slug (skips wizard)"
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite even if local files were modified"
    ),
) -> None:
    """Re-fetch installed agents from registry templates.

    Per-agent merge: clean agents are overwritten silently; modified agents
    prompt for confirmation (the entire agent dir is overwritten as a unit).
    settings.json is always merged to preserve user-tunable keys.
    """
    zdir = zenve_dir(repo_root)
    if not zdir.exists():
        console.print(
            "[red]✗[/red] No [cyan].zenve/[/cyan] directory found. Run [bold]zenve init[/bold] first."
        )
        raise typer.Exit(1)

    agents_dir = zdir / "agents"
    existing_agent_slugs: set[str] = set()
    if agents_dir.exists():
        existing_agent_slugs = {p.name for p in agents_dir.iterdir() if p.is_dir()}

    if not existing_agent_slugs:
        console.print("[dim]No installed agents found.[/dim]")
        raise typer.Exit(0)

    try:
        existing_settings: dict = json.loads((zdir / "settings.json").read_bytes())
    except Exception:
        existing_settings = {}

    svc = _make_template_service()
    lock = AgentLockService(zdir)

    try:
        templates = svc.list_templates()
    except ZenveError as exc:
        console.print(
            f"[red]✗[/red] Could not fetch agent templates: {exc.message}", highlight=False
        )
        raise typer.Exit(1)  # noqa: B904

    # Map: installed slug -> template
    installed_templates: dict[str, object] = {}
    for t in templates:
        slug = _resolve_template_slug(t)
        if slug in existing_agent_slugs:
            installed_templates[slug] = t

    if not installed_templates:
        console.print("[dim]No installed agents match any available template.[/dim]")
        raise typer.Exit(0)

    head_sha = svc.get_head_sha()

    def is_up_to_date(slug: str) -> bool:
        if head_sha is None:
            return False
        entry = lock.get_entry(slug)
        if not entry:
            return False
        return (
            lock.status(slug) == "clean"
            and entry.get("sourceCommitSha") == head_sha
        )

    # Resolve selection
    if agent is not None:
        if agent not in installed_templates:
            console.print(
                f"[red]✗[/red] Agent [bold]{agent}[/bold] is not installed or has no matching template."
            )
            raise typer.Exit(1)
        if is_up_to_date(agent) and not force:
            console.print(
                f"[dim]◆[/dim] [white]{agent}[/white] [dim]is already up to date "
                f"({head_sha[:7] if head_sha else '?'}). Use --force to re-fetch.[/dim]"
            )
            raise typer.Exit(0)
        selected_slugs = [agent]
    else:
        choices = []
        for slug, t in installed_templates.items():
            status = lock.status(slug)
            up_to_date = is_up_to_date(slug)
            if up_to_date:
                label, style = "up to date", "dim green"
            else:
                label, style = _STATUS_LABEL[status]
            title = Text()
            title.append(slug, style="white")
            title.append("  ")
            title.append(f"({label})", style=style)
            choices.append(
                questionary.Choice(
                    title=title.plain,
                    value=slug,
                    disabled="up to date" if up_to_date and not force else None,
                )
            )

        if all(getattr(c, "disabled", None) for c in choices):
            console.print("[dim]All installed agents are already up to date.[/dim]")
            raise typer.Exit(0)

        selected_slugs = questionary.checkbox(
            "Select agents to update",
            choices=choices,
            style=WIZARD_STYLE,
            qmark="◆",
        ).ask()
        sep()

        if not selected_slugs:
            console.print("[dim]No agents selected.[/dim]")
            raise typer.Exit(0)

    # Filter by status with prompts (unless --force)
    to_update: list[str] = []
    for slug in selected_slugs:
        status = lock.status(slug)
        if status == "clean" or force:
            to_update.append(slug)
            continue
        if status == "modified":
            ok = questionary.confirm(
                f"{slug} has local modifications — overwrite the entire agent?",
                default=False,
                style=WIZARD_STYLE,
                qmark="◆",
            ).ask()
        elif status == "unknown":
            ok = questionary.confirm(
                f"{slug} is not in agents-lock.json — overwrite anyway?",
                default=False,
                style=WIZARD_STYLE,
                qmark="◆",
            ).ask()
        else:  # missing
            ok = False
        if ok:
            to_update.append(slug)
        else:
            console.print(f"  [dim]↷[/dim] [dim]{slug} skipped[/dim]")

    if not to_update:
        console.print("[dim]Nothing to update.[/dim]")
        raise typer.Exit(0)

    sep()
    console.print("[cyan]◆[/cyan] [white]Updating agent files...[/white]")
    sep()

    scaffold = ScaffoldingService()
    commit_sha = svc.get_head_sha()
    source = svc.repo or DEFAULT_REGISTRY_REPO
    updated_slugs: list[str] = []

    for slug in to_update:
        template = installed_templates[slug]
        template_id = template.id
        agent_name = template.name if getattr(template, "name", None) else template_id
        try:
            agent_slug, files = build_agent_files(agent_name, template_id, svc)
        except ZenveError as exc:
            console.print(
                f"[yellow]Warning:[/yellow] could not fetch template '{template_id}': {exc.message}"
            )
            continue
        scaffold.write_agent_files_with_merge(zdir, agent_slug, files)
        lock.record_install(
            slug=agent_slug,
            template_id=template_id,
            files=files,
            source=source,
            commit_sha=commit_sha,
        )
        updated_slugs.append(agent_slug)
        console.print(f"  [green]✓[/green] [white]{agent_slug}[/white]")

    sep()
    console.print(
        f"[cyan]◆[/cyan] [white]Updated {len(updated_slugs)} agent(s): "
        f"{', '.join(updated_slugs)}[/white]"
    )
    sep()

    do_commit = questionary.confirm(
        "Commit and push .zenve/?",
        default=True,
        style=WIZARD_STYLE,
        qmark="◆",
    ).ask()
    sep()

    if do_commit:
        branch = existing_settings.get("default_branch", "main")
        _do_commit(
            repo_root,
            f"[zenve] update {len(updated_slugs)} agent(s): {', '.join(updated_slugs)}",
            branch=branch,
        )
    else:
        console.print(
            "[cyan]◆[/cyan] [white]Commit and push [cyan].zenve/[/cyan] to activate[/white]"
        )
    console.print()

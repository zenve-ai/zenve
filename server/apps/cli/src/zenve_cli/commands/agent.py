from __future__ import annotations

import json
from pathlib import Path

import questionary
import typer
from rich.console import Console
from rich.text import Text

from zenve_cli.commands.init import (
    DEFAULT_AGENTS_REPO,
    WIZARD_STYLE,
    collect_agents_wizard,
    sep,
)
from zenve_cli.commands.snapshot import resolve_github_token
from zenve_cli.core.config import zenve_dir
from zenve_cli.core.discovery import AGENTS_SUBDIR, discover_agents
from zenve_cli.models.settings import AgentSettings
from zenve_cli.runtime.commit import GitError, commit_zenve_dir
from zenve_config.settings import get_settings
from zenve_models.agent import AgentCreate
from zenve_models.errors import ZenveError
from zenve_services.template import GitHubTemplateService
from zenve_utils.scaffolding import build_settings_json, default_files, slugify

agent_app = typer.Typer(help="Agent management commands")
console = Console()


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
    override: bool = typer.Option(
        False, "--override", help="Show and re-install already-installed agents"
    ),
) -> None:
    """Add new agents to an already-initialized project."""
    zdir = zenve_dir(repo_root)
    if not zdir.exists():
        console.print(
            "[red]✗[/red] No [cyan].zenve/[/cyan] directory found. Run [bold]zenve init[/bold] first."
        )
        raise typer.Exit(1)

    # Load existing settings and pipeline
    try:
        existing_settings: dict = json.loads((zdir / "settings.json").read_bytes())
    except Exception:
        existing_settings = {}
    existing_pipeline: dict = existing_settings.get("pipeline", {})

    # Collect already-installed agent slugs
    agents_dir = zdir / "agents"
    existing_agent_slugs: set[str] = set()
    if agents_dir.exists():
        existing_agent_slugs = {p.name for p in agents_dir.iterdir() if p.is_dir()}

    # Fetch templates
    settings = get_settings().model_copy(
        update={
            "github_agents_repo": get_settings().github_agents_repo or DEFAULT_AGENTS_REPO,
            "github_token": get_settings().github_token or resolve_github_token(),
        }
    )
    svc = GitHubTemplateService(settings)

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

    # Check if all templates are already installed (and override not requested)
    if not override:
        available_templates = [
            t
            for t in templates
            if slugify(t.name if hasattr(t, "name") and t.name else t.id)
            not in existing_agent_slugs
        ]
        if not available_templates:
            console.print(
                "[dim]All available agents are already installed. Use [bold]--override[/bold] to re-install.[/dim]"
            )
            raise typer.Exit(0)

    # Run agent selector wizard
    agent_specs = collect_agents_wizard(
        templates,
        existing_slugs=None if override else existing_agent_slugs,
    )

    if not agent_specs:
        console.print("[dim]No agents selected.[/dim]")
        raise typer.Exit(0)

    # Scaffold selected agents
    console.print("[cyan]◆[/cyan] [white]Scaffolding agent files...[/white]")
    sep()

    pipeline: dict[str, None] = {}

    for agent_name, template_id in agent_specs:
        agent_slug = slugify(agent_name)
        pipeline[f"zenve:{agent_slug}"] = None

        if template_id:
            try:
                files = svc.fetch_template_files(template_id)
                manifest = svc.get_template(template_id)
                merged = AgentCreate(
                    name=agent_name,
                    template=template_id,
                    adapter_type=manifest.adapter_type,
                    adapter_config=manifest.adapter_config,
                    skills=manifest.skills,
                    tools=manifest.tools,
                    heartbeat_interval_seconds=manifest.heartbeat_interval_seconds,
                )
            except ZenveError as exc:
                console.print(
                    f"[yellow]Warning:[/yellow] could not fetch template '{template_id}': {exc.message}"
                )
                files = default_files()
                merged = AgentCreate(name=agent_name)
        else:
            files = default_files()
            merged = AgentCreate(name=agent_name)

        files["settings.json"] = build_settings_json(merged, agent_slug)
        agent_out = zdir / "agents" / agent_slug
        for relpath, content in files.items():
            dest = agent_out / relpath
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)

    # Merge pipeline back into settings.json
    merged_pipeline = existing_pipeline | pipeline
    updated_settings = {**existing_settings, "pipeline": merged_pipeline}
    (zdir / "settings.json").write_bytes(json.dumps(updated_settings, indent=2).encode())

    added_slugs = [slugify(n) for n, _ in agent_specs]
    console.print(
        f"[cyan]◆[/cyan] [white]Added {len(added_slugs)} agent(s): {', '.join(added_slugs)}[/white]"
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
        try:
            committed = commit_zenve_dir(
                repo_root,
                f"[zenve] add {len(added_slugs)} agent(s): {', '.join(added_slugs)}",
                branch=branch,
            )
            if committed:
                console.print(
                    "[cyan]◆[/cyan] [white]Committed and pushed [cyan].zenve/[/cyan] — activated[/white]"
                )
            else:
                console.print("[yellow]◆[/yellow] [white]Nothing to commit[/white]")
        except GitError as exc:
            console.print(f"[red]✗[/red] Git error: {exc}")
    else:
        console.print(
            "[cyan]◆[/cyan] [white]Commit and push [cyan].zenve/[/cyan] to activate[/white]"
        )
    console.print()


@agent_app.command("update")
def update(
    repo_root: Path = typer.Option(Path("."), "--repo"),
) -> None:
    """Re-fetch installed agents from GitHub templates (pick which ones to update)."""
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

    # Load existing settings
    try:
        existing_settings: dict = json.loads((zdir / "settings.json").read_bytes())
    except Exception:
        existing_settings = {}

    # Fetch templates
    settings = get_settings().model_copy(
        update={
            "github_agents_repo": get_settings().github_agents_repo or DEFAULT_AGENTS_REPO,
            "github_token": get_settings().github_token or resolve_github_token(),
        }
    )
    svc = GitHubTemplateService(settings)

    try:
        templates = svc.list_templates()
    except ZenveError as exc:
        console.print(
            f"[red]✗[/red] Could not fetch agent templates: {exc.message}", highlight=False
        )
        raise typer.Exit(1)  # noqa: B904

    # Filter to only templates that match installed agents
    installed_templates = [
        t
        for t in templates
        if slugify(t.name if hasattr(t, "name") and t.name else t.id) in existing_agent_slugs
    ]

    if not installed_templates:
        console.print("[dim]No installed agents match any available template.[/dim]")
        raise typer.Exit(0)

    # Let user pick which installed agents to update
    choices = [
        questionary.Choice(
            title=t.name if hasattr(t, "name") and t.name else t.id,
            value=t,
        )
        for t in installed_templates
    ]

    selected = questionary.checkbox(
        "Select agents to update",
        choices=choices,
        style=WIZARD_STYLE,
        qmark="◆",
    ).ask()

    sep()

    if not selected:
        console.print("[dim]No agents selected.[/dim]")
        raise typer.Exit(0)

    console.print("[cyan]◆[/cyan] [white]Updating agent files...[/white]")
    sep()

    updated_slugs: list[str] = []

    for template in selected:
        template_id = template.id
        agent_name = template.name if hasattr(template, "name") and template.name else template_id
        agent_slug = slugify(agent_name)

        try:
            files = svc.fetch_template_files(template_id)
            manifest = svc.get_template(template_id)
            merged = AgentCreate(
                name=agent_name,
                template=template_id,
                adapter_type=manifest.adapter_type,
                adapter_config=manifest.adapter_config,
                skills=manifest.skills,
                tools=manifest.tools,
                heartbeat_interval_seconds=manifest.heartbeat_interval_seconds,
            )
        except ZenveError as exc:
            console.print(
                f"[yellow]Warning:[/yellow] could not fetch template '{template_id}': {exc.message}"
            )
            continue

        # Overwrite template files; for settings.json merge to preserve user overrides
        agent_out = zdir / "agents" / agent_slug
        existing_settings_path = agent_out / "settings.json"
        for relpath, content in files.items():
            if relpath == "settings.json" and existing_settings_path.exists():
                existing_raw = json.loads(existing_settings_path.read_text(encoding="utf-8"))
                new_raw = json.loads(build_settings_json(merged, agent_slug))
                user_override_keys = {"name", "slug", "github_label", "enabled", "model", "picks_up", "timeout_seconds"}
                merged_raw = {**new_raw, **{k: v for k, v in existing_raw.items() if k in user_override_keys}}
                content = json.dumps(merged_raw, indent=2).encode()
            dest = agent_out / relpath
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)

        updated_slugs.append(agent_slug)
        console.print(f"  [green]✓[/green] [white]{agent_slug}[/white]")

    sep()
    console.print(
        f"[cyan]◆[/cyan] [white]Updated {len(updated_slugs)} agent(s): {', '.join(updated_slugs)}[/white]"
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
        try:
            committed = commit_zenve_dir(
                repo_root,
                f"[zenve] update {len(updated_slugs)} agent(s): {', '.join(updated_slugs)}",
                branch=branch,
            )
            if committed:
                console.print(
                    "[cyan]◆[/cyan] [white]Committed and pushed [cyan].zenve/[/cyan][/white]"
                )
            else:
                console.print("[yellow]◆[/yellow] [white]Nothing to commit[/white]")
        except GitError as exc:
            console.print(f"[red]✗[/red] Git error: {exc}")
    else:
        console.print(
            "[cyan]◆[/cyan] [white]Commit and push [cyan].zenve/[/cyan] to activate[/white]"
        )
    console.print()

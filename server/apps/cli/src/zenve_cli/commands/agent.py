from __future__ import annotations

import base64
import json
from pathlib import Path

import questionary
import typer
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from zenve_cli.commands.ui import WIZARD_STYLE, sep
from zenve_cli.models.errors import ZenveError
from zenve_cli.models.github_template import GitHubTemplateSummary
from zenve_cli.runtime.client import (
    ensure_runtime,
    report_error,
    resolve_workspace_id,
    runtime_request,
)
from zenve_cli.services.agent import build_agent_files
from zenve_cli.services.agent_lock import AgentLockService
from zenve_cli.services.scaffolding import ScaffoldingService
from zenve_cli.utils.scaffolding import slugify
from zenve_engine.config import zenve_dir
from zenve_engine.discovery import AGENTS_SUBDIR, discover_agents
from zenve_engine.git.commit import GitError, commit_zenve_dir
from zenve_engine.models.settings import AgentSettings

agent_app = typer.Typer(help="Agent management commands")
console = Console()


def resolve_template_slug(t) -> str:
    return t.slug or slugify(t.name if getattr(t, "name", None) else t.id)


def do_commit(repo_root: Path, message: str, branch: str) -> None:
    try:
        committed = commit_zenve_dir(repo_root, message, branch=branch)
        if committed:
            console.print(
                "[cyan]◆[/cyan] Committed and pushed [cyan].zenve/[/cyan]"
            )
        else:
            console.print("[yellow]◆[/yellow] Nothing to commit")
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


@agent_app.command("ls")
def list_agents(repo_root: Path = typer.Option(Path("."), "--repo")) -> None:
    """List all agents and their enabled/disabled status."""
    dirs = iter_agent_dirs(repo_root)
    if not dirs:
        console.print()
        console.print("  [dim]No agents found.[/dim]")
        console.print()
        return

    table = Table(
        box=box.ROUNDED,
        border_style="dim",
        header_style="bold cyan",
        show_lines=False,
        pad_edge=True,
    )
    table.add_column("AGENT", style="cyan", no_wrap=True)
    table.add_column("SLUG", style="dim", no_wrap=True)
    table.add_column("STATUS", justify="center")
    table.add_column("PICKS UP")
    table.add_column("LABEL")
    table.add_column("MODEL", style="dim")

    for d in dirs:
        s = load_agent_settings(d)
        if s is None:
            table.add_row(d.name, d.name, Text("missing settings.json", style="dim red"), "—", "—", "—")
            continue

        status = Text("● on", style="bold green") if s.enabled else Text("○ off", style="dim red")
        model = str(s.adapter_config.get("model", "")) or "—"
        table.add_row(s.name, s.slug, status, s.picks_up, s.github_label, model)

    console.print()
    console.print(table)
    console.print()


@agent_app.command("logs")
def logs(name: str, repo_root: Path = typer.Option(Path("."), "--repo")) -> None:
    """Show run history for a specific agent."""
    ensure_runtime()
    workspace_id = resolve_workspace_id(repo_root)
    resp = runtime_request("GET", f"/api/v1/workspaces/{workspace_id}/runs?limit=50")
    if resp.status_code != 200:
        report_error(resp)
        raise typer.Exit(1)
    runs = resp.json()
    found = False
    for run in runs:
        for a in run.get("agents", []):
            if a.get("agent") != name:
                continue
            found = True
            typer.echo(
                f"  {run.get('run_id', '?'):<24} {a.get('status', '?'):<14} "
                f"{a.get('finished_at') or a.get('started_at') or '?'}"
            )
    if not found:
        typer.echo(f"No runs for agent {name!r}.")


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


def fetch_templates() -> list[GitHubTemplateSummary]:
    """Fetch template list from the runtime. Raises typer.Exit on failure."""
    ensure_runtime()
    resp = runtime_request("GET", "/api/v1/templates")
    if resp.status_code != 200:
        report_error(resp)
        raise typer.Exit(1)
    return [GitHubTemplateSummary(**t) for t in resp.json()]


def fetch_template_files(template_id: str) -> tuple[dict[str, bytes], str | None, str]:
    """Fetch and decode template files from runtime. Returns (files, sha, source)."""
    resp = runtime_request("GET", f"/api/v1/templates/{template_id}/files")
    if resp.status_code != 200:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise ZenveError(f"HTTP {resp.status_code}: {detail}")
    data = resp.json()
    files = {k: base64.b64decode(v) for k, v in data["files"].items()}
    return files, data.get("sha"), data["source"]


@agent_app.command("add")
def add(
    repo_root: Path = typer.Option(Path("."), "--repo"),
    agent: str | None = typer.Option(
        None, "--agent", help="Install a specific template by slug (skips wizard)"
    ),
) -> None:
    """Add new agents to an already-initialized workspace."""
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

    try:
        templates = fetch_templates()
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
            (t for t in templates if t.id == agent or resolve_template_slug(t) == agent),
            None,
        )
        if match is None:
            console.print(
                f"[red]✗[/red] No template found for slug [bold]{agent}[/bold]."
            )
            raise typer.Exit(1)
        target_slug = resolve_template_slug(match)
        if target_slug in existing_agent_slugs:
            console.print(
                f"[yellow]◆[/yellow] Agent [bold]{target_slug}[/bold] is already installed. "
                f"Use [bold]zenve agent update --agent {target_slug}[/bold] to re-fetch."
            )
            raise typer.Exit(0)
        agent_specs = [(match.name if getattr(match, "name", None) else match.id, match.id)]
    else:
        available_templates = [
            t for t in templates if resolve_template_slug(t) not in existing_agent_slugs
        ]
        if not available_templates:
            console.print(
                "[dim]All available agents are already installed. "
                "Use [bold]zenve agent update[/bold] to re-fetch.[/dim]"
            )
            raise typer.Exit(0)

        agent_specs = collect_agents_wizard(templates, existing_slugs=existing_agent_slugs)
        sep()
        if not agent_specs:
            console.print("[dim]No agents selected.[/dim]")
            raise typer.Exit(0)

    # Scaffold + record lock
    console.print("[cyan]◆[/cyan] Scaffolding agent files...")
    sep()

    scaffold = ScaffoldingService()
    lock = AgentLockService(zdir)
    pipeline: dict[str, None] = {}

    for agent_name, template_id in agent_specs:
        template_obj = next((t for t in templates if t.id == template_id), None)
        used_template_id: str | None = template_id
        try:
            raw_files, commit_sha, source = fetch_template_files(template_id)
            agent_slug, files = build_agent_files(agent_name, template_obj, raw_files)
        except ZenveError as exc:
            console.print(
                f"[yellow]Warning:[/yellow] could not fetch template '{template_id}': {exc.message}"
            )
            agent_slug, files = build_agent_files(agent_name, None, {})
            used_template_id = None
            commit_sha = None
            source = None
        pipeline[f"zenve:{agent_slug}"] = None
        scaffold.write_agent_files(zdir, agent_slug, files)
        if used_template_id is not None:
            lock.record_install(
                slug=agent_slug,
                template_id=used_template_id,
                files=files,
                source=source,
                commit_sha=commit_sha,
            )
        console.print(f"  [green]✓[/green] {agent_slug}")

    scaffold.update_pipeline(zdir, pipeline)

    added_slugs = list(pipeline.keys() - set(existing_pipeline.keys()))
    sep()
    console.print(
        f"[cyan]◆[/cyan] Added {len(added_slugs)} agent(s): "
        f"{', '.join(added_slugs)}"
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
        do_commit(
            repo_root,
            f"[zenve] add {len(added_slugs)} agent(s): {', '.join(added_slugs)}",
            branch=branch,
        )
    else:
        console.print(
            "[cyan]◆[/cyan] Commit and push [cyan].zenve/[/cyan] to activate"
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

    try:
        templates = fetch_templates()
    except ZenveError as exc:
        console.print(
            f"[red]✗[/red] Could not fetch agent templates: {exc.message}", highlight=False
        )
        raise typer.Exit(1)  # noqa: B904

    # Map: installed slug -> template
    installed_templates: dict[str, GitHubTemplateSummary] = {}
    for t in templates:
        slug = resolve_template_slug(t)
        if slug in existing_agent_slugs:
            installed_templates[slug] = t

    if not installed_templates:
        console.print("[dim]No installed agents match any available template.[/dim]")
        raise typer.Exit(0)

    lock = AgentLockService(zdir)

    # Resolve selection
    if agent is not None:
        if agent not in installed_templates:
            console.print(
                f"[red]✗[/red] Agent [bold]{agent}[/bold] is not installed or has no matching template."
            )
            raise typer.Exit(1)
        selected_slugs = [agent]
    else:
        choices = []
        for slug in installed_templates:
            status = lock.status(slug)
            label, style = _STATUS_LABEL[status]
            title = Text()
            title.append(slug, style="default")
            title.append("  ")
            title.append(f"({label})", style=style)
            choices.append(
                questionary.Choice(
                    title=title.plain,
                    value=slug,
                )
            )

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
    console.print("[cyan]◆[/cyan] Updating agent files...")
    sep()

    scaffold = ScaffoldingService()
    updated_slugs: list[str] = []

    for slug in to_update:
        template = installed_templates[slug]
        template_id = template.id
        agent_name = template.name if getattr(template, "name", None) else template_id
        try:
            raw_files, commit_sha, source = fetch_template_files(template_id)
            agent_slug, files = build_agent_files(agent_name, template, raw_files)
        except ZenveError as exc:
            console.print(
                f"[yellow]Warning:[/yellow] could not fetch template '{template_id}': {exc.message}"
            )
            continue

        # Check if already up to date (using SHA from files response)
        if not force and commit_sha is not None:
            entry = lock.get_entry(slug)
            if entry and lock.status(slug) == "clean" and entry.get("sourceCommitSha") == commit_sha:
                console.print(
                    f"  [dim]◆[/dim] {slug} [dim]is already up to date "
                    f"({commit_sha[:7]}). Use --force to re-fetch.[/dim]"
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
        console.print(f"  [green]✓[/green] {agent_slug}")

    sep()
    console.print(
        f"[cyan]◆[/cyan] Updated {len(updated_slugs)} agent(s): "
        f"{', '.join(updated_slugs)}"
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
        do_commit(
            repo_root,
            f"[zenve] update {len(updated_slugs)} agent(s): {', '.join(updated_slugs)}",
            branch=branch,
        )
    else:
        console.print(
            "[cyan]◆[/cyan] Commit and push [cyan].zenve/[/cyan] to activate"
        )
    console.print()

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import questionary
import typer
from rich.console import Console

from zenve_cli.commands.agent import collect_agents_wizard
from zenve_cli.commands.skill import (
    collect_skills_wizard,
    install_skills,
    installed_skill_names,
    make_skill_svc,
)
from zenve_cli.commands.snapshot import git_remote_slug, resolve_github_token
from zenve_cli.commands.ui import WIZARD_STYLE, sep
from zenve_cli.constants import DEFAULT_AGENTS_REPO, ZENVE_DIR
from zenve_cli.runtime.commit import commit_zenve_dir
from zenve_config.settings import get_settings
from zenve_models.errors import ZenveError
from zenve_services.agent import build_agent_files
from zenve_services.scaffolding import ScaffoldingService
from zenve_services.template import GitHubTemplateService
from zenve_utils.scaffolding import slugify

console = Console()


def git_current_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        branch = result.stdout.strip()
        return branch if branch and branch != "HEAD" else "main"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "main"


def cmd(repo_root: Path = Path("."), description: str | None = None) -> None:
    zenve_dir = repo_root / ZENVE_DIR
    update_mode = zenve_dir.exists()

    existing_settings: dict = {}
    existing_agent_slugs: set[str] = set()
    if update_mode:
        try:
            existing_settings = json.loads((zenve_dir / "settings.json").read_bytes())
        except Exception:
            existing_settings = {}
        agents_dir = zenve_dir / "agents"
        if agents_dir.exists():
            existing_agent_slugs = {p.name for p in agents_dir.iterdir() if p.is_dir()}

    # Load templates early so the list is ready before prompts begin
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
        console.print(
            "[red]✗[/red] No agent templates found in zenve-ai/zenve-agents.", highlight=False
        )
        raise typer.Exit(1)

    detected_branch = git_current_branch()

    remote_repo = git_remote_slug(repo_root)
    if not remote_repo:
        console.print(
            "[red]✗[/red] Could not detect git remote origin. "
            "Run `git remote add origin <github-url>` first."
        )
        raise typer.Exit(1)

    if update_mode:
        console.print(
            "[cyan]◆[/cyan] [white]Updating existing [cyan].zenve/[/cyan] configuration[/white]"
        )
        sep()

    console.print(f"[cyan]◆[/cyan] [white]Repository  [cyan]{remote_repo}[/cyan][/white]")
    sep()

    # Derive slug from repo name
    slug = slugify(remote_repo.split("/")[-1].removesuffix(".git"))

    if description is None:
        description = questionary.text(
            "Project description",
            default=existing_settings.get("description", ""),
            style=WIZARD_STYLE,
            qmark="◆",
        ).ask()
        sep()
        if description is None:
            raise typer.Exit(1)

    agent_specs = collect_agents_wizard(templates, existing_agent_slugs if update_mode else None)
    if not agent_specs and not update_mode:
        console.print("[red]✗[/red] No agents selected.", highlight=False)
        raise typer.Exit(1)

    # Scaffolding
    console.print("[cyan]◆[/cyan] [white]Scaffolding project files...[/white]")
    sep()

    scaffold = ScaffoldingService()
    existing_pipeline: dict = existing_settings.get("pipeline", {}) if update_mode else {}
    pipeline: dict[str, None] = {}

    for agent_name, template_id in agent_specs:
        try:
            agent_slug, files = build_agent_files(agent_name, template_id, svc)
        except ZenveError as exc:
            console.print(
                f"[yellow]Warning:[/yellow] could not fetch template '{template_id}': {exc.message}"
            )
            agent_slug, files = build_agent_files(agent_name, None, svc)
        pipeline[f"zenve:{agent_slug}"] = None
        scaffold.write_agent_files(zenve_dir, agent_slug, files)

    # Root settings.json — init-specific (project slug, branch, description from wizard)
    merged_pipeline = existing_pipeline | pipeline
    root_settings = {
        **(existing_settings if update_mode else {}),
        "project": slug,
        "description": description,
        "default_branch": detected_branch,
        "commit_message_prefix": existing_settings.get("commit_message_prefix", "[zenve]"),
        "run_timeout_seconds": existing_settings.get("run_timeout_seconds", 600),
        "pipeline": merged_pipeline,
    }
    (zenve_dir / "settings.json").parent.mkdir(parents=True, exist_ok=True)
    (zenve_dir / "settings.json").write_bytes(json.dumps(root_settings, indent=2).encode())

    # Skills step
    skill_svc = make_skill_svc()
    try:
        available_skills = skill_svc.list_skills()
    except ZenveError:
        available_skills = []

    if available_skills:
        selected_skill_ids = collect_skills_wizard(
            available_skills,
            installed=installed_skill_names(repo_root),
        )
        sep()
        if selected_skill_ids:
            console.print("[cyan]◆[/cyan] [white]Installing skills...[/white]")
            sep()
            install_skills(repo_root, selected_skill_ids, skill_svc)
            sep()

    agent_names = list(pipeline.keys())
    if update_mode:
        if agent_names:
            console.print(
                f"[cyan]◆[/cyan] [white]Updated settings and added {len(agent_names)} new agent(s): {', '.join(agent_names)}[/white]"
            )
        else:
            console.print("[cyan]◆[/cyan] [white]Updated settings (no new agents added)[/white]")
    else:
        console.print(
            f"[cyan]◆[/cyan] [white]Initialized with {len(agent_names)} agent(s): {', '.join(agent_names)}[/white]"
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
        commit_msg = "[zenve] update" if update_mode else "[zenve] init"
        committed = commit_zenve_dir(repo_root, commit_msg, branch=detected_branch)
        if committed:
            console.print(
                "[cyan]◆[/cyan] [white]Committed and pushed [cyan].zenve/[/cyan] — activated[/white]"
            )
        else:
            console.print("[yellow]◆[/yellow] [white]Nothing to commit[/white]")
    else:
        console.print(
            "[cyan]◆[/cyan] [white]Commit and push [cyan].zenve/[/cyan] to activate[/white]"
        )
    console.print()

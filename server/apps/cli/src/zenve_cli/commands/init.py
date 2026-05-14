from __future__ import annotations

import json
import subprocess
from pathlib import Path

import questionary
import typer
from rich.console import Console

from zenve_cli.commands.agent import collect_agents_wizard
from zenve_cli.commands.skill import collect_skills_wizard, installed_skill_names
from zenve_cli.commands.snapshot import git_remote_slug
from zenve_cli.commands.ui import WIZARD_STYLE, sep
from zenve_cli.models.github_template import GitHubTemplateSummary, SkillSummary
from zenve_cli.runtime.client import ensure_runtime, report_error, runtime_request
from zenve_cli.utils.scaffolding import slugify
from zenve_engine.constants import ZENVE_DIR
from zenve_engine.git.commit import commit_zenve_dir

console = Console()

STACK_CHOICES = [
    "react",
    "python",
    "fastapi",
    "node",
    "typescript",
    "swift",
    "kotlin",
    "ruby",
    "go",
    "java",
]


def collect_stack_wizard(default: list[str] | None = None) -> list[str]:
    default_set = set(default or [])
    choices = [
        questionary.Choice(title=s, value=s, checked=s in default_set) for s in STACK_CHOICES
    ]
    selected = questionary.checkbox(
        "Project stack",
        choices=choices,
        style=WIZARD_STYLE,
        qmark="◆",
        instruction="(space to toggle, enter to confirm)",
    ).ask()
    return selected or []


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


def fetch_templates() -> list[GitHubTemplateSummary]:
    ensure_runtime()
    resp = runtime_request("GET", "/api/v1/templates")
    if resp.status_code != 200:
        report_error(resp)
        raise typer.Exit(1)
    return [GitHubTemplateSummary(**t) for t in resp.json()]


def fetch_available_skills() -> list[SkillSummary]:
    resp = runtime_request("GET", "/api/v1/skills")
    if resp.status_code != 200:
        return []
    return [SkillSummary(**s) for s in resp.json()]


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

    try:
        templates = fetch_templates()
    except SystemExit:
        raise
    if not templates:
        console.print("[red]✗[/red] No agent templates found.", highlight=False)
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
        console.print("[cyan]◆[/cyan] Updating existing [cyan].zenve/[/cyan] configuration")
        sep()

    console.print(f"[cyan]◆[/cyan] Repository  [cyan]{remote_repo}[/cyan]")
    sep()

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

    stack = collect_stack_wizard(existing_settings.get("stack") or [])
    sep()

    agent_specs = collect_agents_wizard(templates, existing_agent_slugs if update_mode else None)
    if not agent_specs and not update_mode:
        console.print("[red]✗[/red] No agents selected.", highlight=False)
        raise typer.Exit(1)

    available_skills = fetch_available_skills()
    selected_skill_ids: list[str] = []
    if available_skills:
        selected_skill_ids = collect_skills_wizard(
            available_skills,
            installed=installed_skill_names(repo_root),
        )
        sep()

    agent_template_ids = [template_id for _, template_id in agent_specs if template_id]

    console.print("[cyan]◆[/cyan] Initializing workspace via runtime...")
    sep()

    resp = runtime_request(
        "POST",
        "/api/v1/workspaces/init",
        json={
            "name": slug,
            "path": str(repo_root.expanduser().resolve()),
            "description": description,
            "default_branch": detected_branch,
            "stack": stack,
            "agents": agent_template_ids,
            "skills": selected_skill_ids,
        },
    )
    if resp.status_code not in (200, 201, 409):
        report_error(resp)
        raise typer.Exit(1)

    if resp.status_code == 409:
        console.print("[yellow]◆[/yellow] Workspace already registered")

    # Update .gitignore
    gitignore_path = repo_root / ".gitignore"
    gitignore_entries = [".zenve/snapshot.json", ".zenve/events.log"]
    existing_gitignore = gitignore_path.read_text() if gitignore_path.exists() else ""
    missing_entries = [e for e in gitignore_entries if e not in existing_gitignore.splitlines()]
    if missing_entries:
        with gitignore_path.open("a") as f:
            if existing_gitignore and not existing_gitignore.endswith("\n"):
                f.write("\n")
            f.write("\n".join(missing_entries) + "\n")

    agent_count = len(agent_template_ids)
    skill_count = len(selected_skill_ids)
    if update_mode:
        console.print(
            f"[cyan]◆[/cyan] Updated: {agent_count} agent(s), {skill_count} skill(s)"
        )
    else:
        console.print(
            f"[cyan]◆[/cyan] Initialized with {agent_count} agent(s), {skill_count} skill(s)"
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
            console.print("[cyan]◆[/cyan] Committed and pushed [cyan].zenve/[/cyan] — activated")
        else:
            console.print("[yellow]◆[/yellow] Nothing to commit")
    else:
        console.print("[cyan]◆[/cyan] Commit and push [cyan].zenve/[/cyan] to activate")

    console.print()

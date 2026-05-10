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
from zenve_cli.config import get_settings
from zenve_cli.models.errors import ZenveError
from zenve_cli.services.agent import build_agent_files
from zenve_cli.services.agent_lock import AgentLockService
from zenve_cli.services.scaffolding import ScaffoldingService
from zenve_cli.services.template import GitHubTemplateService
from zenve_cli.utils.scaffolding import slugify
from zenve_engine.constants import DEFAULT_AGENTS_PATH, DEFAULT_REGISTRY_REPO, ZENVE_DIR
from zenve_engine.git.commit import commit_skills, commit_zenve_dir

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
            "github_agents_repo": get_settings().github_agents_repo or DEFAULT_REGISTRY_REPO,
            "github_token": get_settings().github_token or resolve_github_token(),
        }
    )
    svc = GitHubTemplateService(settings, base_path=DEFAULT_AGENTS_PATH)

    try:
        templates = svc.list_templates()
    except ZenveError as exc:
        console.print(
            f"[red]✗[/red] Could not fetch agent templates: {exc.message}", highlight=False
        )
        raise typer.Exit(1)  # noqa: B904

    if not templates:
        console.print(
            f"[red]✗[/red] No agent templates found in {settings.github_agents_repo}/{DEFAULT_AGENTS_PATH}.",
            highlight=False,
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
            "[cyan]◆[/cyan] Updating existing [cyan].zenve/[/cyan] configuration"
        )
        sep()

    console.print(f"[cyan]◆[/cyan] Repository  [cyan]{remote_repo}[/cyan]")
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

    stack = collect_stack_wizard(existing_settings.get("stack") or [])
    sep()

    agent_specs = collect_agents_wizard(templates, existing_agent_slugs if update_mode else None)
    if not agent_specs and not update_mode:
        console.print("[red]✗[/red] No agents selected.", highlight=False)
        raise typer.Exit(1)

    # Scaffolding
    console.print("[cyan]◆[/cyan] Scaffolding project files...")
    sep()

    scaffold = ScaffoldingService()
    lock = AgentLockService(zenve_dir)
    commit_sha = svc.get_head_sha()
    source = svc.repo or DEFAULT_REGISTRY_REPO
    existing_pipeline: dict = existing_settings.get("pipeline", {}) if update_mode else {}
    pipeline: dict[str, None] = {}

    for agent_name, template_id in agent_specs:
        used_template_id: str | None = template_id
        try:
            agent_slug, files = build_agent_files(agent_name, template_id, svc)
        except ZenveError as exc:
            console.print(
                f"[yellow]Warning:[/yellow] could not fetch template '{template_id}': {exc.message}"
            )
            agent_slug, files = build_agent_files(agent_name, None, svc)
            used_template_id = None
        pipeline[f"zenve:{agent_slug}"] = None
        scaffold.write_agent_files(zenve_dir, agent_slug, files)
        if used_template_id is not None:
            lock.record_install(
                slug=agent_slug,
                template_id=used_template_id,
                files=files,
                source=source,
                commit_sha=commit_sha,
            )

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
        "stack": stack,
    }
    (zenve_dir / "settings.json").parent.mkdir(parents=True, exist_ok=True)
    (zenve_dir / "settings.json").write_bytes(json.dumps(root_settings, indent=2).encode())

    # Append zenve runtime files to .gitignore if not already present
    gitignore_path = repo_root / ".gitignore"
    gitignore_entries = [".zenve/snapshot.json", ".zenve/events.log"]
    existing_gitignore = gitignore_path.read_text() if gitignore_path.exists() else ""
    missing_entries = [e for e in gitignore_entries if e not in existing_gitignore.splitlines()]
    if missing_entries:
        with gitignore_path.open("a") as f:
            if existing_gitignore and not existing_gitignore.endswith("\n"):
                f.write("\n")
            f.write("\n".join(missing_entries) + "\n")

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
            console.print("[cyan]◆[/cyan] Installing skills...")
            sep()
            install_skills(repo_root, selected_skill_ids, skill_svc)
            sep()
            commit_skills(repo_root, "[zenve] install skills", branch=detected_branch)

    agent_names = list(pipeline.keys())
    if update_mode:
        if agent_names:
            console.print(
                f"[cyan]◆[/cyan] Updated settings and added {len(agent_names)} new agent(s): {', '.join(agent_names)}"
            )
        else:
            console.print("[cyan]◆[/cyan] Updated settings (no new agents added)")
    else:
        console.print(
            f"[cyan]◆[/cyan] Initialized with {len(agent_names)} agent(s): {', '.join(agent_names)}"
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
                "[cyan]◆[/cyan] Committed and pushed [cyan].zenve/[/cyan] — activated"
            )
        else:
            console.print("[yellow]◆[/yellow] Nothing to commit")
    else:
        console.print(
            "[cyan]◆[/cyan] Commit and push [cyan].zenve/[/cyan] to activate"
        )

    register_with_runtime(repo_root)
    console.print()


def register_with_runtime(repo_root: Path) -> None:
    """Best-effort registration of the workspace with the local runtime."""
    import httpx

    from zenve_cli.runtime.client import runtime_url

    abs_path = repo_root.expanduser().resolve()
    url = f"{runtime_url()}/api/v1/workspaces"
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(url, json={"path": str(abs_path)})
    except httpx.ConnectError:
        console.print(
            "[yellow]◆[/yellow] Runtime not running — run [cyan]zenve workspace add .[/cyan] later to register"
        )
        return

    if resp.status_code == 201:
        console.print("[cyan]◆[/cyan] Registered with runtime")
    elif resp.status_code == 409:
        console.print("[cyan]◆[/cyan] Already registered with runtime")
    else:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        console.print(f"[yellow]◆[/yellow] Could not register ({resp.status_code}): {detail}")

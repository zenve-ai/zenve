from __future__ import annotations

import json
import subprocess
from pathlib import Path

import questionary
import typer
from questionary import Choice
from rich.console import Console

from zenve_config.settings import get_settings
from zenve_models.agent import AgentCreate
from zenve_models.errors import ZenveError
from zenve_services.template import GitHubTemplateService
from zenve_utils.scaffolding import build_settings_json, default_files, slugify

ZENVE_DIR = ".zenve"
DEFAULT_AGENTS_REPO = "zenve-ai/agents"
console = Console()

WIZARD_STYLE = questionary.Style(
    [
        ("qmark", "fg:#00d4ff bold"),
        ("question", "fg:#ffffff bold"),
        ("answer", "fg:#00d4ff bold"),
        ("pointer", "fg:#00d4ff bold"),
        ("highlighted", "fg:#00d4ff bold"),
        ("selected", "fg:#00d4ff"),
        ("instruction", "fg:#555555"),
        ("text", "fg:#aaaaaa"),
        ("disabled", "fg:#444444 italic"),
    ]
)

# ANSI Shadow-style ZENVE logo (6 rows)
LOGO = """███████╗ ███████╗ ███╗   ██╗ ██╗   ██╗ ███████╗
╚══███╔╝ ██╔════╝ ████╗  ██║ ██║   ██║ ██╔════╝
  ███╔╝  █████╗   ██╔██╗ ██║ ██║   ██║ █████╗
 ███╔╝   ██╔══╝   ██║╚██╗██║ ╚██╗ ██╔╝ ██╔══╝
███████╗ ███████╗ ██║ ╚████║  ╚████╔╝  ███████╗
╚══════╝ ╚══════╝ ╚═╝  ╚═══╝   ╚═══╝   ╚══════╝"""


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


def print_logo() -> None:
    console.print()
    console.print(LOGO, style="bold cyan")
    console.print()


def sep() -> None:
    """Print the connecting │ line between wizard steps."""
    console.print("[dim]│[/dim]")


def collect_agents_wizard(
    templates: list, existing_slugs: set[str] | None = None
) -> list[tuple[str, str | None]]:
    """Collect agent specs via checkbox."""
    existing_slugs = existing_slugs or set()
    choices = []
    for t in templates:
        agent_slug = slugify(t.name if hasattr(t, "name") and t.name else t.id)
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

    print_logo()

    # Load templates early so the list is ready before prompts begin
    settings = get_settings()
    if not settings.github_agents_repo:
        settings = settings.model_copy(update={"github_agents_repo": DEFAULT_AGENTS_REPO})
    svc = GitHubTemplateService(settings)

    try:
        templates = svc.list_templates()
    except ZenveError as exc:
        console.print(
            f"[red]✗[/red] Could not fetch agent templates: {exc.message}", highlight=False
        )
        raise typer.Exit(1)  # noqa: B904

    if not templates:
        console.print("[red]✗[/red] No agent templates found in zenve-ai/agents.", highlight=False)
        raise typer.Exit(1)

    detected_branch = git_current_branch()

    if update_mode:
        console.print(
            "[cyan]◆[/cyan] [white]Updating existing [cyan].zenve/[/cyan] configuration[/white]"
        )
        sep()

    repo_path = questionary.text(
        "GitHub repository  (username/repo)",
        default=existing_settings.get("repo", ""),
        style=WIZARD_STYLE,
        qmark="◆",
        validate=lambda v: (
            True
            if len(v.strip().split("/")) == 2 and not v.startswith("http")
            else "Enter in format: username/repo"
        ),
    ).ask()
    sep()
    if repo_path is None:
        raise typer.Exit(1)

    # Derive slug from repo name — no separate prompt
    slug = slugify(repo_path.strip().split("/")[-1].removesuffix(".git"))

    name = questionary.text(
        "Project name",
        default=existing_settings.get("project", ""),
        style=WIZARD_STYLE,
        qmark="◆",
    ).ask()
    sep()
    if not name:
        raise typer.Exit(1)

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

    all_files: dict[str, bytes] = {}
    existing_pipeline: dict = existing_settings.get("pipeline", {}) if update_mode else {}
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
        for relpath, content in files.items():
            all_files[f"agents/{agent_slug}/{relpath}"] = content

    merged_pipeline = existing_pipeline | pipeline
    root_settings = {
        **(existing_settings if update_mode else {}),
        "project": slug,
        "description": description,
        "repo": repo_path.strip(),
        "default_branch": detected_branch,
        "commit_message_prefix": existing_settings.get("commit_message_prefix", "[zenve]"),
        "run_timeout_seconds": existing_settings.get("run_timeout_seconds", 600),
        "pipeline": merged_pipeline,
    }
    all_files["settings.json"] = json.dumps(root_settings, indent=2).encode()

    for relpath, content in all_files.items():
        dest = zenve_dir / relpath
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)

    agent_names = [slugify(n) for n, _ in agent_specs]
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
    console.print("[cyan]◆[/cyan] [white]Commit and push [cyan].zenve/[/cyan] to activate[/white]")
    console.print()

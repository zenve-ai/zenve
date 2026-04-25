from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import typer

from zenve_models.agent import AgentCreate
from zenve_models.errors import ZenveError
from zenve_services.template import GitHubTemplateService
from zenve_utils.scaffolding import build_settings_json, default_files, slugify

ZENVE_DIR = ".zenve"


@dataclass
class TemplateSettings:
    github_agents_repo: str | None
    github_token: str | None


def git_remote_url() -> str | None:
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


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


def collect_agents_from_templates(svc: GitHubTemplateService) -> list[tuple[str, str | None]]:
    """Returns list of (agent_name, template_id|None) chosen by the user."""
    try:
        templates = svc.list_templates()
    except ZenveError as exc:
        typer.echo(f"Warning: could not fetch templates: {exc.message}", err=True)
        return collect_blank_agents()

    if not templates:
        typer.echo("No templates found in repo — falling back to blank agent.")
        return collect_blank_agents()

    typer.echo("\nAvailable agent templates:\n")
    for i, t in enumerate(templates, 1):
        desc = f"  {t.description}" if t.description else ""
        typer.echo(f"  [{i}] {t.name} ({t.id}){desc}")
    typer.echo(f"  [0] Blank agent (no template)")
    typer.echo("")

    raw = typer.prompt("Select templates by number (comma-separated, e.g. 1,3)")
    chosen: list[tuple[str, str | None]] = []
    for part in raw.split(","):
        part = part.strip()
        if not part.isdigit():
            continue
        idx = int(part)
        if idx == 0:
            name = typer.prompt("Agent name")
            chosen.append((name, None))
        elif 1 <= idx <= len(templates):
            tmpl = templates[idx - 1]
            default_name = tmpl.name
            name = typer.prompt(f"Agent name for '{tmpl.id}'", default=default_name)
            chosen.append((name, tmpl.id))
    return chosen if chosen else collect_blank_agents()


def collect_blank_agents() -> list[tuple[str, str | None]]:
    """Prompt for one or more blank agent names."""
    agents: list[tuple[str, str | None]] = []
    while True:
        name = typer.prompt("Agent name")
        agents.append((name, None))
        if not typer.confirm("Add another agent?", default=False):
            break
    return agents


def cmd(repo_root: Path = Path("."), description: str | None = None) -> None:
    zenve_dir = repo_root / ZENVE_DIR
    if zenve_dir.exists():
        typer.echo(f"✗ .zenve/ already exists at {zenve_dir}", err=True)
        raise typer.Exit(1)

    # Determine repo URL
    repo_url = git_remote_url()
    if not repo_url:
        repo_url = typer.prompt("GitHub repo (e.g. owner/repo or full URL)")

    # Determine default branch
    default_branch = git_current_branch()

    # Collect agents
    github_token = os.environ.get("GITHUB_TOKEN")
    github_agents_repo = os.environ.get("GITHUB_AGENTS_REPO")

    if github_token and github_agents_repo:
        svc = GitHubTemplateService(TemplateSettings(  # type: ignore[arg-type]
            github_agents_repo=github_agents_repo,
            github_token=github_token,
        ))
        agent_specs = collect_agents_from_templates(svc)
    else:
        agent_specs = collect_blank_agents()

    if not agent_specs:
        typer.echo("✗ No agents selected.", err=True)
        raise typer.Exit(1)

    # Prompt for description
    if description is None:
        description = typer.prompt("Project description", default="")

    # Derive project name from repo URL
    repo_slug = repo_url.rstrip("/").split("/")[-1].removesuffix(".git")

    # Build file tree
    all_files: dict[str, bytes] = {}
    pipeline: dict[str, None] = {}

    for agent_name, template_id in agent_specs:
        slug = slugify(agent_name)
        pipeline[f"zenve:{slug}"] = None

        if template_id and github_token and github_agents_repo:
            svc = GitHubTemplateService(TemplateSettings(  # type: ignore[arg-type]
                github_agents_repo=github_agents_repo,
                github_token=github_token,
            ))
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
                typer.echo(f"Warning: could not fetch template '{template_id}': {exc.message}", err=True)
                files = default_files()
                merged = AgentCreate(name=agent_name)
        else:
            files = default_files()
            merged = AgentCreate(name=agent_name)

        files["settings.json"] = build_settings_json(merged, slug)
        for relpath, content in files.items():
            all_files[f"agents/{slug}/{relpath}"] = content

    root_settings = {
        "project": repo_slug,
        "description": description,
        "repo": repo_url,
        "default_branch": default_branch,
        "commit_message_prefix": "[zenve]",
        "run_timeout_seconds": 600,
        "pipeline": pipeline,
    }
    all_files["settings.json"] = json.dumps(root_settings, indent=2).encode()

    # Write files locally
    for relpath, content in all_files.items():
        dest = zenve_dir / relpath
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)

    agent_names = [slugify(name) for name, _ in agent_specs]
    typer.echo(f"\n✓ Initialized .zenve/ with {len(agent_names)} agent(s): {', '.join(agent_names)}")
    typer.echo("  Commit and push .zenve/ to your repo to activate.")

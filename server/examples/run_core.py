"""
Example: run one agent with zenve_core.

Sets up a temporary git repo and .zenve/ config, installs the zenve-issues
skill from the runtime, then runs a single agent against a message.

Usage:
    just runtime          # start runtime first
    uv run python examples/run_core.py

Requirements:
    - `claude` CLI installed and authenticated
    - Zenve runtime running on localhost:8001
"""

from __future__ import annotations

import asyncio
import base64
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import httpx

from zenve_core import run_agent

RUNTIME_URL = "http://localhost:8001"

SOUL_MD = """\
You are a helpful Python developer agent.
"""

AGENTS_MD = """\
# Instructions
You are a Python developer. When asked to work on a task, write clean Python code.
Signal completion with RUN_COMPLETED at the end of your last message.
"""

MESSAGE = "Work on issue #1"


def install_skill(project_dir: Path, skill_id: str) -> None:
    """Download skill files from the runtime and install into the project."""
    try:
        resp = httpx.get(f"{RUNTIME_URL}/api/v1/skills/{skill_id}/files", timeout=10)
        resp.raise_for_status()
    except httpx.ConnectError:
        print(f"ERROR: Runtime not reachable at {RUNTIME_URL}. Run `just runtime` first.")
        sys.exit(1)
    except httpx.HTTPStatusError as exc:
        print(f"ERROR: Could not fetch skill {skill_id!r}: {exc}")
        sys.exit(1)

    files = {k: base64.b64decode(v) for k, v in resp.json()["files"].items()}

    skill_dir = project_dir / ".agents" / "skills" / skill_id
    skill_dir.mkdir(parents=True)
    for relpath, content in files.items():
        dest = skill_dir / relpath
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)

    link = project_dir / ".claude" / "skills" / skill_id
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(Path("../../.agents/skills") / skill_id)


def setup_project(project_dir: Path) -> None:
    zenve_dir = project_dir / ".zenve"
    zenve_dir.mkdir()

    (zenve_dir / "settings.json").write_text(json.dumps({
        "project": "test-project",
        "description": "A test project for zenve_core",
        "default_branch": "main",
        "stack": ["Python"],
    }, indent=2))

    agent_dir = zenve_dir / "agents" / "dev"
    agent_dir.mkdir(parents=True)

    (agent_dir / "settings.json").write_text(json.dumps({
        "slug": "dev",
        "name": "Dev Agent",
        "adapter_type": "claude_code",
        "adapter_config": {"model": "claude-sonnet-4-6", "max_turns": 5},
        "github_label": "zenve:dev",
        "mode": "no_pr",
        "tools": ["Read", "Write", "Edit", "Bash"],
    }, indent=2))

    (agent_dir / "SOUL.md").write_text(SOUL_MD)
    (agent_dir / "AGENTS.md").write_text(AGENTS_MD)


def run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


def init_git_repo(project_dir: Path) -> None:
    run(["git", "init", "-b", "main"], project_dir)
    run(["git", "config", "user.email", "test@example.com"], project_dir)
    run(["git", "config", "user.name", "Test"], project_dir)
    (project_dir / "README.md").write_text("# Test Project\n")
    run(["git", "add", "."], project_dir)
    run(["git", "commit", "-m", "init"], project_dir)


async def main() -> None:
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    tmp_path = Path(__file__).parent / "run_core" / f"run_{run_id}"
    tmp_path.mkdir(parents=True)

    project_dir = tmp_path / "repo"
    project_dir.mkdir()

    init_git_repo(project_dir)
    setup_project(project_dir)
    install_skill(project_dir, "zenve-issues")

    print(f"Project dir : {project_dir}")
    print(f"Message     : {MESSAGE!r}\n")

    def on_event(event: dict) -> None:
        t = event.get("type", "")
        agent = event.get("agent") or ""
        data = event.get("data") or {}
        msg = data.get("message") or ""
        prefix = f"[{agent}] " if agent else ""
        if t.startswith("adapter.output") and msg:
            print(f"  {prefix}{msg}", flush=True)
        elif not t.startswith("adapter."):
            print(f"  {t} {prefix}{str(data)[:120] if data else ''}")

    result = await run_agent(
        project_dir,
        "dev",
        MESSAGE,
        on_event=on_event,
    )

    print(f"\n{'='*60}")
    print(f"run_id    : {result.run_id}")
    print(f"status    : {result.status}")
    print(f"exit_code : {result.exit_code}")
    print(f"duration  : {result.duration_seconds:.2f}s")
    if result.token_usage:
        print(f"tokens    : in={result.token_usage.input_tokens} out={result.token_usage.output_tokens}")
    if result.error:
        print(f"error     : {result.error}")


if __name__ == "__main__":
    asyncio.run(main())

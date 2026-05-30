from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from zenve_adapters import AdapterRegistry, build_default_registry
from zenve_core.errors import AgentNotFoundError
from zenve_core.execution import execute
from zenve_core.result import AgentRunResult
from zenve_engine.config import load_project_settings
from zenve_engine.discovery import discover_agents
from zenve_engine.events.emitter import EventEmitter


async def run_agent(
    project_dir: Path,
    agent_slug: str,
    message: str,
    *,
    workspace_id: str = "",
    registry: AdapterRegistry | None = None,
    env_vars: dict[str, str] | None = None,
    on_event: Callable[[dict], None] | None = None,
    cancel_event: asyncio.Event | None = None,
) -> AgentRunResult:
    """Execute one agent against one message in an isolated worktree.

    The agent owns all git operations (commit, push, PR) via its tools.
    zenve_core creates the worktree and cleans it up — nothing else.
    """
    run_id = uuid4().hex
    project = load_project_settings(project_dir)

    agents = discover_agents(project_dir, only=agent_slug)
    if not agents:
        raise AgentNotFoundError(agent_slug)
    agent = agents[0]

    base_env: dict[str, str] = {
        "ZENVE_RUN_ID": run_id,
        "ZENVE_WORKSPACE_ID": workspace_id,
        "GH_TOKEN": os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or "",
        **(env_vars or {}),
    }

    emitter = EventEmitter(repo_root=project_dir, run_id=run_id, on_event=on_event)

    return await execute(
        agent=agent,
        project=project,
        project_dir=project_dir,
        run_id=run_id,
        message=message,
        env_vars=base_env,
        registry=registry or build_default_registry(),
        emitter=emitter,
        workspace_id=workspace_id,
        cancel_event=cancel_event,
    )

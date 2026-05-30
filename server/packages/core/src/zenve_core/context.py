from __future__ import annotations

from pathlib import Path

from zenve_adapters.models import RunContext
from zenve_core.discovery import DiscoveredAgent
from zenve_core.models.settings import WorkspaceSettings


def build_run_context(
    agent: DiscoveredAgent,
    run_id: str,
    workspace: WorkspaceSettings,
    workspace_dir: Path,
    message: str,
    env_vars: dict[str, str],
    workspace_id: str = "",
    workspace_dir_override: Path | None = None,
) -> RunContext:
    effective_dir = workspace_dir_override if workspace_dir_override is not None else workspace_dir
    return RunContext(
        agent_dir=str(agent.path),
        workspace_dir=str(effective_dir.resolve()),
        agent_id=agent.settings.slug,
        agent_slug=agent.settings.slug,
        agent_name=agent.settings.name,
        workspace_slug=workspace.slug,
        workspace_id=workspace_id,
        workspace_description=workspace.description,
        workspace_stack=list(workspace.stack),
        run_id=run_id,
        adapter_type=agent.settings.adapter_type,
        adapter_config=dict(agent.settings.adapter_config),
        message=message,
        heartbeat=False,
        tools=agent.settings.tools,
        env_vars=env_vars,
    )

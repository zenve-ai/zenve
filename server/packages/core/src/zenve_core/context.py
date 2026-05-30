from __future__ import annotations

from pathlib import Path

from zenve_adapters.models import RunContext
from zenve_engine.discovery import DiscoveredAgent
from zenve_engine.models.settings import ProjectSettings


def build_run_context(
    agent: DiscoveredAgent,
    run_id: str,
    project: ProjectSettings,
    project_dir: Path,
    message: str,
    env_vars: dict[str, str],
    workspace_id: str = "",
    project_dir_override: Path | None = None,
) -> RunContext:
    effective_dir = project_dir_override if project_dir_override is not None else project_dir
    return RunContext(
        agent_dir=str(agent.path),
        project_dir=str(effective_dir.resolve()),
        agent_id=agent.settings.slug,
        agent_slug=agent.settings.slug,
        agent_name=agent.settings.name,
        project_slug=project.project,
        workspace_id=workspace_id,
        project_description=project.description,
        project_stack=list(project.stack),
        run_id=run_id,
        adapter_type=agent.settings.adapter_type,
        adapter_config=dict(agent.settings.adapter_config),
        message=message,
        heartbeat=False,
        tools=agent.settings.tools,
        env_vars=env_vars,
    )

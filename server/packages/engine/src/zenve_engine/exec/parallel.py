from __future__ import annotations

import asyncio
from pathlib import Path

from zenve_adapters import AdapterRegistry
from zenve_engine.discovery import DiscoveredAgent
from zenve_engine.events.emitter import EventEmitter
from zenve_engine.exec.executor import DryRunResult, run_agent
from zenve_engine.github.client import GitHubClient
from zenve_engine.models.run_result import RunResultFile
from zenve_engine.models.settings import ProjectSettings
from zenve_engine.models.snapshot import Snapshot


async def run_all(
    agents: list[DiscoveredAgent],
    snapshot: Snapshot,
    project: ProjectSettings,
    repo_root: Path,
    run_id: str,
    registry: AdapterRegistry,
    gh: GitHubClient,
    emitter: EventEmitter,
    env_vars: dict[str, str],
    dry_run: bool = False,
) -> list[DryRunResult | RunResultFile | None]:
    """Start every enabled agent concurrently via `asyncio.gather`."""
    coros = [
        run_agent(
            agent=agent,
            snapshot=snapshot,
            project=project,
            repo_root=repo_root,
            run_id=run_id,
            registry=registry,
            gh=gh,
            emitter=emitter,
            env_vars=env_vars,
            dry_run=dry_run,
        )
        for agent in agents
    ]
    return await asyncio.gather(*coros)

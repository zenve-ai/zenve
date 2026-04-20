from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from zenve_cli.core.config import zenve_dir
from zenve_cli.models.settings import AgentSettings

AGENTS_SUBDIR = "agents"


class DiscoveryError(RuntimeError):
    """Raised when an agent directory is invalid."""


@dataclass(frozen=True)
class DiscoveredAgent:
    name: str
    path: Path
    settings: AgentSettings


def discover_agents(repo_root: Path, only: str | None = None) -> list[DiscoveredAgent]:
    """Scan `.zenve/agents/*` for agent directories.

    - Each agent dir must contain a `settings.json`.
    - Skips agents with `enabled: false`.
    - If `only` is given, filters to just that agent (still skipped if disabled).
    - Sorts results by name for deterministic ordering.
    """
    agents_dir = zenve_dir(repo_root) / AGENTS_SUBDIR
    if not agents_dir.exists():
        return []

    results: list[DiscoveredAgent] = []
    for child in sorted(agents_dir.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith("."):
            continue
        settings_path = child / "settings.json"
        if not settings_path.exists():
            continue
        try:
            raw = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DiscoveryError(f"Invalid JSON in {settings_path}: {exc}") from exc
        try:
            settings = AgentSettings.model_validate(raw)
        except ValidationError as exc:
            raise DiscoveryError(f"Invalid settings in {settings_path}: {exc}") from exc

        if not settings.enabled:
            continue
        if only is not None and settings.name != only:
            continue
        results.append(DiscoveredAgent(name=settings.name, path=child, settings=settings))

    return results

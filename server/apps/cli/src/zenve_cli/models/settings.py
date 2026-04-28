from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

PicksUp = Literal["issues", "pull_requests", "both", "none"]


class ProjectSettings(BaseModel):
    """Shape of `.zenve/settings.json`."""

    model_config = {"extra": "ignore"}

    project: str
    default_branch: str = "main"
    commit_message_prefix: str = "[zenve]"
    run_timeout_seconds: int = 600
    pipeline: dict[str, str | None] = Field(default_factory=dict)


class AgentSettings(BaseModel):
    """Shape of `.zenve/agents/{name}/settings.json`."""

    model_config = {"extra": "ignore"}

    slug: str
    name: str
    model: str = "claude-sonnet-4-6"
    adapter_type: str = "claude_code"
    enabled: bool = True
    github_label: str
    timeout_seconds: int = 300
    picks_up: PicksUp = "issues"

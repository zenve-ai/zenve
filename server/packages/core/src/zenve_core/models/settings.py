from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

PicksUp = Literal["issues", "pull_requests", "both", "none"]


class IssuesConfig(BaseModel):
    """Per-workspace issues adapter override in `.zenve/settings.json`.

    When `adapter` is None the runtime's default adapter is used.
    """

    model_config = {"extra": "ignore"}

    adapter: str | None = None


class WorkspaceSettings(BaseModel):
    """Shape of `.zenve/settings.json`."""

    model_config = {"extra": "ignore"}

    slug: str
    description: str = ""
    default_branch: str = "main"
    commit_message_prefix: str = "[zenve]"
    run_timeout_seconds: int = 600
    pipeline: dict[str, str | None] = Field(default_factory=dict)
    stack: list[str] = Field(default_factory=list)
    issues: IssuesConfig = Field(default_factory=IssuesConfig)


class AgentSettings(BaseModel):
    """Shape of `.zenve/agents/{name}/settings.json`."""

    model_config = {"extra": "ignore"}

    slug: str
    name: str
    adapter_type: str = "claude_code"
    adapter_config: dict = Field(default_factory=dict)
    skills: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    heartbeat_interval_seconds: int = 0
    enabled: bool = True
    github_label: str
    timeout_seconds: int = 300
    picks_up: PicksUp = "both"
    mode: Literal["artifact_pr", "code_pr", "no_pr", "review_pr"] = "no_pr"
    allowed_paths: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def review_pr_only_picks_up_prs(self) -> AgentSettings:
        if self.mode == "review_pr" and self.picks_up != "pull_requests":
            self.picks_up = "pull_requests"
        return self

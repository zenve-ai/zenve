from __future__ import annotations

from pydantic import BaseModel, Field


class GlobalSettings(BaseModel):
    issues_adapter: str = "github"


class GlobalSettingsUpdate(BaseModel):
    issues_adapter: str | None = None


class IssuesConfig(BaseModel):
    adapter: str | None = None


class WorkspaceSettings(BaseModel):
    project: str
    description: str = ""
    default_branch: str = "main"
    commit_message_prefix: str = "[zenve]"
    run_timeout_seconds: int = 600
    run_schedule: str | None = None
    stack: list[str] = Field(default_factory=list)
    pipeline: dict[str, str | None] = Field(default_factory=dict)
    issues: IssuesConfig = Field(default_factory=IssuesConfig)


class WorkspaceSettingsUpdate(BaseModel):
    description: str | None = None
    default_branch: str | None = None
    commit_message_prefix: str | None = None
    run_timeout_seconds: int | None = None
    run_schedule: str | None = None
    stack: list[str] | None = None
    pipeline: dict[str, str | None] | None = None
    issues: IssuesConfig | None = None

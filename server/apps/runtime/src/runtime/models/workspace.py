from __future__ import annotations

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    path: str


class Workspace(BaseModel):
    id: str
    path: str
    registered_at: str


class WorkspaceDetail(Workspace):
    project: str
    description: str = ""
    default_branch: str = "main"
    run_schedule: str | None = None
    pipeline: dict[str, str | None] = Field(default_factory=dict)
    stack: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)
    repo: str | None = None

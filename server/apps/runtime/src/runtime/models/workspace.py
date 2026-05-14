from __future__ import annotations

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    path: str


class ScaffoldWorkspaceBody(BaseModel):
    name: str
    path: str
    description: str = ""
    default_branch: str = "main"
    stack: list[str] = []
    agents: list[str] = []
    skills: list[str] = []


class Workspace(BaseModel):
    id: str
    path: str
    registered_at: str
    agent_count: int = 0


class AgentSummary(BaseModel):
    slug: str
    name: str
    adapter_type: str = ""
    model: str = ""
    skills: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    enabled: bool = True
    mode: str = ""


class WorkspaceDetail(Workspace):
    project: str
    description: str = ""
    default_branch: str = "main"
    run_schedule: str | None = None
    pipeline: dict[str, str | None] = Field(default_factory=dict)
    stack: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)
    repo: str | None = None

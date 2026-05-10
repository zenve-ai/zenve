from typing import Any

from pydantic import BaseModel, ConfigDict


class AgentSummary(BaseModel):
    name: str
    slug: str
    adapter_type: str
    enabled: bool


class AgentDetail(AgentSummary):
    adapter_config: dict
    skills: list[str]
    tools: list[str]
    heartbeat_interval_seconds: int
    has_soul: bool
    has_agents: bool
    has_heartbeat: bool
    files: list[str]


class RunSummary(BaseModel):
    run_id: str
    status: str | None = None
    started_at: str | None = None


class RunDetail(RunSummary):
    data: dict


class ProjectSettings(BaseModel):
    model_config = ConfigDict(extra="allow")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectSettings":
        return cls.model_validate(data)

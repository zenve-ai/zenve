from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    name: str
    adapter_type: str
    adapter_config: dict = {}
    skills: list[str] = []
    tools: list[str] = []
    heartbeat_interval_seconds: int = 0
    template: str = "default"
    """Template set name under `TEMPLATES_DIR` (e.g. `default`)."""
    template_vars: dict[str, Any] | None = Field(
        default=None,
        description="Extra Jinja context for the chosen template set; keys depend on that template.",
    )
    role: str | None = None


class AgentUpdate(BaseModel):
    name: str | None = None
    adapter_config: dict | None = None
    skills: list[str] | None = None
    tools: list[str] | None = None
    status: str | None = None
    heartbeat_interval_seconds: int | None = None


class AgentResponse(BaseModel):
    id: str
    org_id: str
    name: str
    slug: str
    dir_path: str
    adapter_type: str
    adapter_config: dict
    skills: list[str]
    tools: list[str]
    status: str
    heartbeat_interval_seconds: int
    last_heartbeat_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentFileList(BaseModel):
    files: list[str]


class AgentFileContent(BaseModel):
    path: str
    content: str

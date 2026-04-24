from pydantic import BaseModel


class AgentCreate(BaseModel):
    name: str
    adapter_type: str
    adapter_config: dict = {}
    skills: list[str] = []
    tools: list[str] = ["Read", "Write", "Bash"]
    heartbeat_interval_seconds: int = 0
    template: str | None = None


class AgentUpdate(BaseModel):
    name: str | None = None
    adapter_config: dict | None = None
    skills: list[str] | None = None
    tools: list[str] | None = None
    enabled: bool | None = None
    heartbeat_interval_seconds: int | None = None


class AgentFileList(BaseModel):
    files: list[str]


class AgentFileContent(BaseModel):
    path: str
    content: str

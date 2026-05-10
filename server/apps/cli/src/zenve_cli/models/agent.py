from pydantic import BaseModel


class AgentCreate(BaseModel):
    name: str
    adapter_type: str = "claude_code"
    adapter_config: dict = {}
    skills: list[str] = []
    tools: list[str] = ["Read", "Write", "Bash"]
    heartbeat_interval_seconds: int = 0
    mode: str = "no_pr"
    template: str | None = None

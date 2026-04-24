from pydantic import BaseModel


class GitHubTemplateSummary(BaseModel):
    id: str
    name: str
    description: str = ""
    adapter_type: str = "claude_code"
    adapter_config: dict = {}
    skills: list[str] = []
    tools: list[str] = ["Read", "Write", "Bash"]
    heartbeat_interval_seconds: int = 0


class AgentCreateFromGitHubTemplate(BaseModel):
    template_id: str
    name: str | None = None

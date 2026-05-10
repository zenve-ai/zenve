from pydantic import BaseModel


class GitHubTemplateSummary(BaseModel):
    id: str
    name: str
    slug: str | None = None
    description: str = ""
    adapter_type: str = "claude_code"
    adapter_config: dict = {}
    skills: list[str] = []
    tools: list[str] = ["Read", "Write", "Bash"]
    heartbeat_interval_seconds: int = 0
    mode: str = "no_pr"


class AgentCreateFromGitHubTemplate(BaseModel):
    template_id: str
    name: str | None = None


class SkillSummary(BaseModel):
    id: str
    name: str
    description: str = ""

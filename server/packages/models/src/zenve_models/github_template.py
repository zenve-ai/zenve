from pydantic import BaseModel


class GitHubTemplateSummary(BaseModel):
    id: str
    name: str
    description: str = ""
    adapter_type: str = "claude_code"


class AgentCreateFromGitHubTemplate(BaseModel):
    template_id: str
    name: str | None = None

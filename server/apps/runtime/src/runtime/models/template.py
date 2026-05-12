from pydantic import BaseModel


class TemplateItem(BaseModel):
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


class TemplateFilesResponse(BaseModel):
    sha: str | None = None
    source: str
    files: dict[str, str]  # relative path → base64-encoded content


class SkillItem(BaseModel):
    id: str
    name: str
    description: str = ""


class SkillFilesResponse(BaseModel):
    files: dict[str, str]  # relative path → base64-encoded content

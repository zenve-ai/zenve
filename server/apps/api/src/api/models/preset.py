from pydantic import BaseModel


class PresetSummary(BaseModel):
    name: str
    description: str = ""


class Preset(BaseModel):
    name: str
    description: str = ""
    adapter_type: str = "claude_code"
    template: str = "default"
    template_vars: dict[str, str] = {}
    adapter_config: dict = {}
    skills: list[str] = []
    tools: list[str] = ["Read", "Write", "Bash"]
    heartbeat_interval_seconds: int = 0

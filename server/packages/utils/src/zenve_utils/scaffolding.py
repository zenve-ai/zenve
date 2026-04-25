import json
import re

from zenve_models.agent import AgentCreate

DEFAULT_SOUL_MD = b"# Soul\n\nYou are a helpful AI agent.\n"
DEFAULT_AGENTS_MD = b"# Agents\n\nNo collaborators configured.\n"


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def default_files() -> dict[str, bytes]:
    return {
        "SOUL.md": DEFAULT_SOUL_MD,
        "AGENTS.md": DEFAULT_AGENTS_MD,
    }


def build_settings_json(data: AgentCreate, slug: str) -> bytes:
    settings = {
        "name": data.name,
        "adapter_type": data.adapter_type,
        "adapter_config": data.adapter_config,
        "skills": data.skills,
        "tools": data.tools,
        "heartbeat_interval_seconds": data.heartbeat_interval_seconds,
        "github_label": f"zenve:{slug}",
        "enabled": True,
    }
    return json.dumps(settings, indent=2).encode()

import json
import re

from zenve_db.models import Project
from zenve_models.agent import AgentCreate, AgentUpdate
from zenve_models.repo import AgentDetail, AgentSummary
from zenve_services.repo_reader import RepoReaderService
from zenve_services.repo_writer import RepoWriterService
from zenve_services.template import GitHubTemplateService


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


DEFAULT_SOUL_MD = b"# Soul\n\nYou are a helpful AI agent.\n"
DEFAULT_AGENTS_MD = b"# Agents\n\nNo collaborators configured.\n"


def default_files() -> dict[str, bytes]:
    return {
        "SOUL.md": DEFAULT_SOUL_MD,
        "AGENTS.md": DEFAULT_AGENTS_MD,
    }


def build_settings_json(data: AgentCreate) -> bytes:
    settings = {
        "name": data.name,
        "adapter_type": data.adapter_type,
        "adapter_config": data.adapter_config,
        "skills": data.skills,
        "tools": data.tools,
        "heartbeat_interval_seconds": data.heartbeat_interval_seconds,
        "enabled": True,
    }
    return json.dumps(settings, indent=2).encode()


class AgentService:
    def __init__(
        self,
        reader: RepoReaderService,
        writer: RepoWriterService,
        template_service: GitHubTemplateService,
    ):
        self.reader = reader
        self.writer = writer
        self.template_service = template_service

    def list(self, project: Project) -> list[AgentSummary]:
        return self.reader.list_agents(project)

    def get(self, project: Project, name: str) -> AgentDetail:
        return self.reader.get_agent(project, name)

    def create(self, project: Project, data: AgentCreate) -> AgentDetail:
        slug = slugify(data.name)
        if data.template:
            files = self.template_service.fetch_template_files(data.template)
        else:
            files = default_files()
        files["settings.json"] = build_settings_json(data)
        self.writer.scaffold_agent(project, slug, files, f"feat(agents): create agent {slug}")
        return self.reader.get_agent(project, slug)

    def update(self, project: Project, name: str, data: AgentUpdate) -> AgentDetail:
        agent = self.reader.get_agent(project, name)
        settings = {
            "name": agent.name,
            "adapter_type": agent.adapter_type,
            "adapter_config": agent.adapter_config,
            "skills": agent.skills,
            "tools": agent.tools,
            "heartbeat_interval_seconds": agent.heartbeat_interval_seconds,
            "enabled": agent.enabled,
        }
        if data.name is not None:
            settings["name"] = data.name
        if data.adapter_config is not None:
            settings["adapter_config"] = data.adapter_config
        if data.skills is not None:
            settings["skills"] = data.skills
        if data.tools is not None:
            settings["tools"] = data.tools
        if data.heartbeat_interval_seconds is not None:
            settings["heartbeat_interval_seconds"] = data.heartbeat_interval_seconds
        if data.enabled is not None:
            settings["enabled"] = data.enabled
        self.writer.write_file(
            project,
            name,
            "settings.json",
            json.dumps(settings, indent=2).encode(),
            f"feat(agents): update agent {name} settings",
        )
        return self.reader.get_agent(project, name)

    def delete(self, project: Project, name: str) -> None:
        self.writer.delete_agent(project, name, f"feat(agents): delete agent {name}")

    def write_file(self, project: Project, name: str, relpath: str, content: bytes) -> None:
        self.writer.write_file(
            project,
            name,
            relpath,
            content,
            f"feat(agents): update {name}/{relpath}",
        )

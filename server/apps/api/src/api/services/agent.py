import json

from api.db.models import Workspace
from api.models.agent import AgentCreate, AgentUpdate
from api.models.errors import ConflictError, NotFoundError
from api.models.workspace import WorkspaceInit
from api.models.repo import AgentDetail, AgentSummary
from api.services.repo_reader import RepoReaderService
from api.services.repo_writer import RepoWriterService
from api.services.template import GitHubTemplateService
from api.utils.scaffolding import build_settings_json, default_files, slugify


def build_agent_files(
    name: str,
    template_id: str | None,
    template_service: GitHubTemplateService,
) -> tuple[str, dict[str, bytes]]:
    slug = slugify(name)
    if template_id:
        files = template_service.fetch_template_files(template_id)
        manifest = template_service.get_template(template_id)
        slug = manifest.slug or slug
        merged = AgentCreate(
            name=name,
            template=template_id,
            adapter_type=manifest.adapter_type,
            adapter_config=manifest.adapter_config,
            skills=manifest.skills,
            tools=manifest.tools,
            heartbeat_interval_seconds=manifest.heartbeat_interval_seconds,
            mode=manifest.mode,
        )
    else:
        files = default_files()
        merged = AgentCreate(name=name)
    files["settings.json"] = build_settings_json(merged, slug)
    return slug, files


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

    def get_all(self, workspace: Workspace) -> list[AgentSummary]:
        return self.reader.list_agents(workspace)

    def get(self, workspace: Workspace, name: str) -> AgentDetail:
        return self.reader.get_agent(workspace, name)

    def create(self, workspace: Workspace, data: AgentCreate) -> AgentDetail:
        initial_slug = slugify(data.name)
        try:
            self.reader.get_agent(workspace, initial_slug)
            raise ConflictError(f"Agent '{initial_slug}' already exists")
        except NotFoundError:
            pass
        slug, files = build_agent_files(data.name, data.template, self.template_service)
        self.writer.scaffold_agent(workspace, slug, files, f"feat(agents): create agent {slug}")
        return self.reader.get_agent(workspace, slug)

    def update(self, workspace: Workspace, name: str, data: AgentUpdate) -> AgentDetail:
        agent = self.reader.get_agent(workspace, name)
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
            workspace,
            name,
            "settings.json",
            json.dumps(settings, indent=2).encode(),
            f"feat(agents): update agent {name} settings",
        )
        return self.reader.get_agent(workspace, name)

    def delete(self, workspace: Workspace, name: str) -> None:
        self.writer.delete_agent(workspace, name, f"feat(agents): delete agent {name}")

    def init(self, workspace: Workspace, data: WorkspaceInit) -> list[AgentSummary]:
        settings = self.reader.get_workspace_settings(workspace)
        if settings:
            raise ConflictError("Workspace already initialized")

        all_files: dict[str, bytes | None] = {}
        pipeline: dict[str, None] = {}

        for spec in data.agents:
            slug, files = build_agent_files(spec.name, spec.template, self.template_service)
            pipeline[f"zenve:{slug}"] = None
            for relpath, content in files.items():
                all_files[f".zenve/agents/{slug}/{relpath}"] = content

        root_settings = {
            "workspace": workspace.name,
            "description": data.description,
            "repo": workspace.github_repo,
            "default_branch": workspace.github_default_branch,
            "commit_message_prefix": "[zenve]",
            "run_timeout_seconds": 600,
            "pipeline": pipeline,
        }
        all_files[".zenve/settings.json"] = json.dumps(root_settings, indent=2).encode()

        self.writer.scaffold_workspace(workspace, all_files, "feat(zenve): initialize workspace")
        return self.reader.list_agents(workspace)

    def write_file(self, workspace: Workspace, name: str, relpath: str, content: bytes) -> None:
        self.writer.write_file(
            workspace,
            name,
            relpath,
            content,
            f"feat(agents): update {name}/{relpath}",
        )

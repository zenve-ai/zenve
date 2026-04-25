import json

from zenve_db.models import Project
from zenve_models.agent import AgentCreate, AgentUpdate
from zenve_models.errors import ConflictError, NotFoundError
from zenve_models.project import ProjectInit
from zenve_models.repo import AgentDetail, AgentSummary
from zenve_services.repo_reader import RepoReaderService
from zenve_services.repo_writer import RepoWriterService
from zenve_services.template import GitHubTemplateService
from zenve_utils.scaffolding import build_settings_json, default_files, slugify


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

    def get_all(self, project: Project) -> list[AgentSummary]:
        return self.reader.list_agents(project)

    def get(self, project: Project, name: str) -> AgentDetail:
        return self.reader.get_agent(project, name)

    def create(self, project: Project, data: AgentCreate) -> AgentDetail:
        slug = slugify(data.name)
        try:
            self.reader.get_agent(project, slug)
            raise ConflictError(f"Agent '{slug}' already exists")
        except NotFoundError:
            pass
        if data.template:
            files = self.template_service.fetch_template_files(data.template)
            manifest = self.template_service.get_template(data.template)
            merged = AgentCreate(
                name=data.name,
                template=data.template,
                adapter_type=manifest.adapter_type,
                adapter_config=manifest.adapter_config,
                skills=manifest.skills,
                tools=manifest.tools,
                heartbeat_interval_seconds=manifest.heartbeat_interval_seconds,
            )
        else:
            files = default_files()
            merged = data
        files["settings.json"] = build_settings_json(merged, slug)
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

    def init(self, project: Project, data: ProjectInit) -> list[AgentSummary]:
        settings = self.reader.get_project_settings(project)
        if settings:
            raise ConflictError("Project already initialized")

        all_files: dict[str, bytes | None] = {}
        pipeline: dict[str, None] = {}

        for spec in data.agents:
            slug = slugify(spec.name)
            pipeline[f"zenve:{slug}"] = None

            if spec.template:
                files = self.template_service.fetch_template_files(spec.template)
                manifest = self.template_service.get_template(spec.template)
                merged = AgentCreate(
                    name=spec.name,
                    template=spec.template,
                    adapter_type=manifest.adapter_type,
                    adapter_config=manifest.adapter_config,
                    skills=manifest.skills,
                    tools=manifest.tools,
                    heartbeat_interval_seconds=manifest.heartbeat_interval_seconds,
                )
            else:
                files = default_files()
                merged = AgentCreate(name=spec.name)
            files["settings.json"] = build_settings_json(merged, slug)
            for relpath, content in files.items():
                all_files[f".zenve/agents/{slug}/{relpath}"] = content

        root_settings = {
            "project": project.name,
            "description": data.description,
            "repo": project.github_repo,
            "default_branch": project.github_default_branch,
            "commit_message_prefix": "[zenve]",
            "run_timeout_seconds": 600,
            "pipeline": pipeline,
        }
        all_files[".zenve/settings.json"] = json.dumps(root_settings, indent=2).encode()

        self.writer.scaffold_project(project, all_files, "feat(zenve): initialize project")
        return self.reader.list_agents(project)

    def write_file(self, project: Project, name: str, relpath: str, content: bytes) -> None:
        self.writer.write_file(
            project,
            name,
            relpath,
            content,
            f"feat(agents): update {name}/{relpath}",
        )

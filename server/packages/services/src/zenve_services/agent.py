import re
import uuid
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zenve_adapters.registry import AdapterRegistry
from zenve_config.settings import get_settings
from zenve_db.models import Agent, Project
from zenve_models.agent import AgentCreate, AgentUpdate
from zenve_models.github_template import AgentCreateFromGitHubTemplate
from zenve_services.template import GitHubTemplateService


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


class AgentService:
    def __init__(
        self,
        db: Session,
        adapter_registry: AdapterRegistry,
        github_template_service: GitHubTemplateService,
    ):
        self.db = db
        self.adapter_registry = adapter_registry
        self.github_template_service = github_template_service

    def create_from_github_template(self, org: Project, data: AgentCreateFromGitHubTemplate) -> Agent:
        if not self.github_template_service.is_enabled():
            raise HTTPException(status_code=503, detail="GitHub agent templates are not configured")
        template = self.github_template_service.get_template(data.template_id)
        name = data.name or template.name
        slug = slugify(name)
        base_path = str(Path(get_settings().data_dir) / "orgs" / org.slug)
        dir_path = self.github_template_service.scaffold_agent_from_template(
            template_id=data.template_id,
            org_slug=org.slug,
            agent_slug=slug,
            base_path=base_path,
        )
        agent_id = str(uuid.uuid4())
        agent = Agent(
            id=agent_id,
            org_id=org.id,
            name=name,
            slug=slug,
            dir_path=dir_path,
            adapter_type=template.adapter_type,
            adapter_config={},
            skills=[],
            tools=[],
            status="active",
        )
        self.db.add(agent)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail="An agent with this name or slug already exists in this organization",
            ) from exc
        self.db.refresh(agent)
        return agent

    def create(self, org: Project, data: AgentCreate) -> Agent:
        if not self.adapter_registry.has(data.adapter_type):
            raise HTTPException(
                status_code=422,
                detail=f"Unknown adapter_type '{data.adapter_type}'. Known types: {self.adapter_registry.known_types()}",
            )

        adapter = self.adapter_registry.get(data.adapter_type)
        default_config = adapter.get_default_config().model_dump(exclude_none=True)
        adapter_config = {**default_config, **data.adapter_config}
        adapter.validate_config(adapter_config)

        slug = slugify(data.name)
        base_path = str(Path(get_settings().data_dir) / "orgs" / org.slug)
        agent_dir = Path(base_path) / "agents" / slug
        if agent_dir.exists():
            raise HTTPException(status_code=409, detail=f"Agent directory already exists: {agent_dir}")
        agent_dir.mkdir(parents=True)
        (agent_dir / "memory").mkdir()
        (agent_dir / "runs").mkdir()
        dir_path = str(agent_dir)

        agent_id = str(uuid.uuid4())
        agent = Agent(
            id=agent_id,
            org_id=org.id,
            name=data.name,
            slug=slug,
            dir_path=dir_path,
            adapter_type=data.adapter_type,
            adapter_config=adapter_config,
            skills=data.skills,
            tools=data.tools,
            status="active",
            heartbeat_interval_seconds=data.heartbeat_interval_seconds,
        )
        self.db.add(agent)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail="An agent with this name or slug already exists in this organization",
            ) from exc
        self.db.refresh(agent)
        return agent

    def get_by_id(self, org_id: str, agent_id: str) -> Agent:
        agent = self.db.query(Agent).filter(Agent.org_id == org_id, Agent.id == agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent

    def get_by_slug(self, org_id: str, slug: str) -> Agent:
        agent = self.db.query(Agent).filter(Agent.org_id == org_id, Agent.slug == slug).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent

    def get_by_id_or_slug(self, org_id: str, identifier: str) -> Agent:
        try:
            uuid.UUID(identifier)
            return self.get_by_id(org_id, identifier)
        except ValueError:
            return self.get_by_slug(org_id, identifier)

    def list_by_org(
        self,
        org_id: str,
        status: str | None = None,
        adapter_type: str | None = None,
    ) -> list[Agent]:
        q = self.db.query(Agent).filter(Agent.org_id == org_id)
        if status:
            q = q.filter(Agent.status == status)
        if adapter_type:
            q = q.filter(Agent.adapter_type == adapter_type)
        return q.all()

    def update(self, org_id: str, agent_id: str, data: AgentUpdate) -> Agent:
        agent = self.get_by_id(org_id, agent_id)

        if data.name is not None:
            agent.name = data.name
        if data.adapter_config is not None:
            agent.adapter_config = data.adapter_config
        if data.skills is not None:
            agent.skills = data.skills
        if data.tools is not None:
            agent.tools = data.tools
        if data.status is not None:
            agent.status = data.status
        if data.heartbeat_interval_seconds is not None:
            agent.heartbeat_interval_seconds = data.heartbeat_interval_seconds

        self.db.commit()
        self.db.refresh(agent)
        return agent

    def archive(self, org_id: str, agent_id: str) -> Agent:
        agent = self.get_by_id(org_id, agent_id)
        agent.status = "archived"
        self.db.commit()
        self.db.refresh(agent)
        return agent

    def get_agent_files(self, agent: Agent) -> list[str]:
        root = Path(agent.dir_path)
        return [str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()]

    def read_agent_file(self, agent: Agent, path: str) -> str:
        full_path = self.validate_path(agent.dir_path, path)
        return Path(full_path).read_text(encoding="utf-8")

    def write_agent_file(self, agent: Agent, path: str, content: str) -> None:
        full_path = self.validate_path(agent.dir_path, path)
        file_path = Path(full_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    def validate_path(self, agent_dir: str, file_path: str) -> str:
        root = Path(agent_dir).resolve()
        resolved = (root / file_path).resolve()
        if not str(resolved).startswith(f"{root}/") and resolved != root:
            raise ValueError(f"Path traversal detected: {file_path!r}")
        return str(resolved)

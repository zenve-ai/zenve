import re
import uuid

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zenve_adapters.registry import AdapterRegistry
from zenve_db.models import Agent, Organization
from zenve_models.agent import AgentCreate, AgentCreateFromPreset, AgentUpdate
from zenve_scaffolding import PresetService, ScaffoldingService
from zenve_services.filesystem import FilesystemService
from zenve_services.template import TemplateService


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


class AgentService:
    def __init__(
        self,
        db: Session,
        filesystem: FilesystemService,
        adapter_registry: AdapterRegistry,
        template_service: TemplateService,
        scaffolding: ScaffoldingService,
        preset_service: PresetService,
    ):
        self.db = db
        self.filesystem = filesystem
        self.adapter_registry = adapter_registry
        self.template_service = template_service
        self.scaffolding = scaffolding
        self.preset_service = preset_service

    def create_from_preset(self, org: Organization, data: AgentCreateFromPreset) -> Agent:
        preset = self.preset_service.load_preset(data.preset)
        create_data = AgentCreate(
            name=data.name or preset.name,
            adapter_type=preset.adapter_type,
            adapter_config=preset.adapter_config,
            template=preset.template,
            template_vars=preset.template_vars,
            skills=preset.skills,
            tools=preset.tools,
            heartbeat_interval_seconds=preset.heartbeat_interval_seconds,
        )
        return self.create(org, create_data)

    def create(self, org: Organization, data: AgentCreate) -> Agent:
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

        template_name = self.template_service.resolve_template_name(data.template)
        self.template_service.validate_vars(template_name, data.template_vars)

        template_vars = {k: v for k, v in data.template_vars.items() if v is not None}

        dir_path = self.scaffolding.scaffold_agent_dir(
            org_slug=org.slug,
            agent_slug=slug,
            base_path=org.base_path,
            template_vars=template_vars,
            template_name=data.template,
        )

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
        return self.filesystem.list_agent_files(agent.dir_path)

    def read_agent_file(self, agent: Agent, path: str) -> str:
        return self.filesystem.read_agent_file(agent.dir_path, path)

    def write_agent_file(self, agent: Agent, path: str, content: str) -> None:
        self.filesystem.write_agent_file(agent.dir_path, path, content)

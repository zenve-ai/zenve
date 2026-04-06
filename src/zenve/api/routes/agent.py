from fastapi import APIRouter, Depends, Query, status

from zenve.db.models import ApiKeyRecord, Organization
from zenve.models.agent import (
    AgentCreate,
    AgentFileContent,
    AgentFileList,
    AgentResponse,
    AgentUpdate,
)
from zenve.services import get_agent_service
from zenve.services.agent import AgentService
from zenve.utils.api_key_auth import require_scope

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(
    body: AgentCreate,
    auth: tuple[Organization, ApiKeyRecord] = Depends(require_scope("agents:write")),
    service: AgentService = Depends(get_agent_service),
):
    org, _ = auth
    return service.create(org, body)


@router.get("", response_model=list[AgentResponse])
def list_agents(
    agent_status: str | None = Query(None, alias="status"),
    adapter_type: str | None = Query(None),
    auth: tuple[Organization, ApiKeyRecord] = Depends(require_scope("agents:read")),
    service: AgentService = Depends(get_agent_service),
):
    org, _ = auth
    return service.list_by_org(org.id, status=agent_status, adapter_type=adapter_type)


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(
    agent_id: str,
    auth: tuple[Organization, ApiKeyRecord] = Depends(require_scope("agents:read")),
    service: AgentService = Depends(get_agent_service),
):
    org, _ = auth
    return service.get_by_id_or_slug(org.id, agent_id)


@router.patch("/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: str,
    body: AgentUpdate,
    auth: tuple[Organization, ApiKeyRecord] = Depends(require_scope("agents:write")),
    service: AgentService = Depends(get_agent_service),
):
    org, _ = auth
    return service.update(org.id, agent_id, body)


@router.delete("/{agent_id}", response_model=AgentResponse)
def archive_agent(
    agent_id: str,
    auth: tuple[Organization, ApiKeyRecord] = Depends(require_scope("agents:write")),
    service: AgentService = Depends(get_agent_service),
):
    org, _ = auth
    return service.archive(org.id, agent_id)


@router.get("/{agent_id}/files", response_model=AgentFileList)
def list_agent_files(
    agent_id: str,
    auth: tuple[Organization, ApiKeyRecord] = Depends(require_scope("agents:read")),
    service: AgentService = Depends(get_agent_service),
):
    org, _ = auth
    agent = service.get_by_id_or_slug(org.id, agent_id)
    return AgentFileList(files=service.get_agent_files(agent))


@router.get("/{agent_id}/files/{path:path}", response_model=AgentFileContent)
def read_agent_file(
    agent_id: str,
    path: str,
    auth: tuple[Organization, ApiKeyRecord] = Depends(require_scope("agents:read")),
    service: AgentService = Depends(get_agent_service),
):
    org, _ = auth
    agent = service.get_by_id_or_slug(org.id, agent_id)
    content = service.read_agent_file(agent, path)
    return AgentFileContent(path=path, content=content)


@router.put("/{agent_id}/files/{path:path}", status_code=status.HTTP_204_NO_CONTENT)
def write_agent_file(
    agent_id: str,
    path: str,
    body: AgentFileContent,
    auth: tuple[Organization, ApiKeyRecord] = Depends(require_scope("agents:write")),
    service: AgentService = Depends(get_agent_service),
):
    org, _ = auth
    agent = service.get_by_id_or_slug(org.id, agent_id)
    service.write_agent_file(agent, path, body.content)

from fastapi import APIRouter, Depends, Query, status

from zenve_db.models import UserRecord
from zenve_models.agent import (
    AgentCreate,
    AgentCreateFromPreset,
    AgentFileContent,
    AgentFileList,
    AgentResponse,
    AgentUpdate,
)
from zenve_services import get_agent_service, get_membership_service, get_project_service
from zenve_services.agent import AgentService
from zenve_services.membership import MembershipService
from zenve_services.project import ProjectService
from zenve_utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/orgs/{org_id}/agents", tags=["agents"])


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(
    org_id: str,
    body: AgentCreate,
    user: UserRecord = Depends(get_current_user),
    org_service: ProjectService = Depends(get_project_service),
    membership_service: MembershipService = Depends(get_membership_service),
    service: AgentService = Depends(get_agent_service),
):
    org = org_service.get_by_id_or_slug(org_id)
    membership_service.require_membership(user.id, org.id)
    return service.create(org, body)


@router.post("/from-preset", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent_from_preset(
    org_id: str,
    body: AgentCreateFromPreset,
    user: UserRecord = Depends(get_current_user),
    org_service: ProjectService = Depends(get_project_service),
    membership_service: MembershipService = Depends(get_membership_service),
    service: AgentService = Depends(get_agent_service),
):
    org = org_service.get_by_id_or_slug(org_id)
    membership_service.require_membership(user.id, org.id)
    return service.create_from_preset(org, body)


@router.get("", response_model=list[AgentResponse])
def list_agents(
    org_id: str,
    agent_status: str | None = Query(None, alias="status"),
    adapter_type: str | None = Query(None),
    user: UserRecord = Depends(get_current_user),
    org_service: ProjectService = Depends(get_project_service),
    membership_service: MembershipService = Depends(get_membership_service),
    service: AgentService = Depends(get_agent_service),
):
    org = org_service.get_by_id_or_slug(org_id)
    membership_service.require_membership(user.id, org.id)
    return service.list_by_org(org.id, status=agent_status, adapter_type=adapter_type)


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(
    org_id: str,
    agent_id: str,
    user: UserRecord = Depends(get_current_user),
    org_service: ProjectService = Depends(get_project_service),
    membership_service: MembershipService = Depends(get_membership_service),
    service: AgentService = Depends(get_agent_service),
):
    org = org_service.get_by_id_or_slug(org_id)
    membership_service.require_membership(user.id, org.id)
    return service.get_by_id_or_slug(org.id, agent_id)


@router.patch("/{agent_id}", response_model=AgentResponse)
def update_agent(
    org_id: str,
    agent_id: str,
    body: AgentUpdate,
    user: UserRecord = Depends(get_current_user),
    org_service: ProjectService = Depends(get_project_service),
    membership_service: MembershipService = Depends(get_membership_service),
    service: AgentService = Depends(get_agent_service),
):
    org = org_service.get_by_id_or_slug(org_id)
    membership_service.require_membership(user.id, org.id)
    return service.update(org.id, agent_id, body)


@router.delete("/{agent_id}", response_model=AgentResponse)
def archive_agent(
    org_id: str,
    agent_id: str,
    user: UserRecord = Depends(get_current_user),
    org_service: ProjectService = Depends(get_project_service),
    membership_service: MembershipService = Depends(get_membership_service),
    service: AgentService = Depends(get_agent_service),
):
    org = org_service.get_by_id_or_slug(org_id)
    membership_service.require_membership(user.id, org.id)
    return service.archive(org.id, agent_id)


@router.get("/{agent_id}/files", response_model=AgentFileList)
def list_agent_files(
    org_id: str,
    agent_id: str,
    user: UserRecord = Depends(get_current_user),
    org_service: ProjectService = Depends(get_project_service),
    membership_service: MembershipService = Depends(get_membership_service),
    service: AgentService = Depends(get_agent_service),
):
    org = org_service.get_by_id_or_slug(org_id)
    membership_service.require_membership(user.id, org.id)
    agent = service.get_by_id_or_slug(org.id, agent_id)
    return AgentFileList(files=service.get_agent_files(agent))


@router.get("/{agent_id}/files/{path:path}", response_model=AgentFileContent)
def read_agent_file(
    org_id: str,
    agent_id: str,
    path: str,
    user: UserRecord = Depends(get_current_user),
    org_service: ProjectService = Depends(get_project_service),
    membership_service: MembershipService = Depends(get_membership_service),
    service: AgentService = Depends(get_agent_service),
):
    org = org_service.get_by_id_or_slug(org_id)
    membership_service.require_membership(user.id, org.id)
    agent = service.get_by_id_or_slug(org.id, agent_id)
    content = service.read_agent_file(agent, path)
    return AgentFileContent(path=path, content=content)


@router.put("/{agent_id}/files/{path:path}", status_code=status.HTTP_204_NO_CONTENT)
def write_agent_file(
    org_id: str,
    agent_id: str,
    path: str,
    body: AgentFileContent,
    user: UserRecord = Depends(get_current_user),
    org_service: ProjectService = Depends(get_project_service),
    membership_service: MembershipService = Depends(get_membership_service),
    service: AgentService = Depends(get_agent_service),
):
    org = org_service.get_by_id_or_slug(org_id)
    membership_service.require_membership(user.id, org.id)
    agent = service.get_by_id_or_slug(org.id, agent_id)
    service.write_agent_file(agent, path, body.content)

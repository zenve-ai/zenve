from fastapi import APIRouter, Depends, status

from api.db.models import UserRecord
from api.models.agent import AgentCreate, AgentFileContent, AgentFileList, AgentUpdate
from api.models.repo import AgentDetail, AgentSummary
from api.services import (
    get_agent_service,
    get_membership_service,
    get_workspace_service,
    get_repo_reader_service,
)
from api.services.agent import AgentService
from api.services.membership import MembershipService
from api.services.workspace import WorkspaceService
from api.services.repo_reader import RepoReaderService
from api.utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/agents", tags=["agents"])


@router.get("", response_model=list[AgentSummary])
def list_agents(
    workspace_id: str,
    user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    membership_service: MembershipService = Depends(get_membership_service),
    service: AgentService = Depends(get_agent_service),
):
    workspace = workspace_service.get_by_id_or_slug(workspace_id)
    membership_service.require_membership(user.id, workspace.id)
    return service.get_all(workspace)


@router.post("", response_model=AgentDetail, status_code=status.HTTP_201_CREATED)
def create_agent(
    workspace_id: str,
    body: AgentCreate,
    user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    membership_service: MembershipService = Depends(get_membership_service),
    service: AgentService = Depends(get_agent_service),
):
    workspace = workspace_service.get_by_id_or_slug(workspace_id)
    membership_service.require_membership(user.id, workspace.id)
    return service.create(workspace, body)


@router.get("/{name}", response_model=AgentDetail)
def get_agent(
    workspace_id: str,
    name: str,
    user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    membership_service: MembershipService = Depends(get_membership_service),
    service: AgentService = Depends(get_agent_service),
):
    workspace = workspace_service.get_by_id_or_slug(workspace_id)
    membership_service.require_membership(user.id, workspace.id)
    return service.get(workspace, name)


@router.patch("/{name}", response_model=AgentDetail)
def update_agent(
    workspace_id: str,
    name: str,
    body: AgentUpdate,
    user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    membership_service: MembershipService = Depends(get_membership_service),
    service: AgentService = Depends(get_agent_service),
):
    workspace = workspace_service.get_by_id_or_slug(workspace_id)
    membership_service.require_membership(user.id, workspace.id)
    return service.update(workspace, name, body)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    workspace_id: str,
    name: str,
    user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    membership_service: MembershipService = Depends(get_membership_service),
    service: AgentService = Depends(get_agent_service),
):
    workspace = workspace_service.get_by_id_or_slug(workspace_id)
    membership_service.require_membership(user.id, workspace.id)
    service.delete(workspace, name)


@router.get("/{name}/files", response_model=AgentFileList)
def list_agent_files(
    workspace_id: str,
    name: str,
    user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    membership_service: MembershipService = Depends(get_membership_service),
    reader: RepoReaderService = Depends(get_repo_reader_service),
):
    workspace = workspace_service.get_by_id_or_slug(workspace_id)
    membership_service.require_membership(user.id, workspace.id)
    return AgentFileList(files=reader.list_agent_files(workspace, name))


@router.get("/{name}/files/{path:path}", response_model=AgentFileContent)
def read_agent_file(
    workspace_id: str,
    name: str,
    path: str,
    user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    membership_service: MembershipService = Depends(get_membership_service),
    reader: RepoReaderService = Depends(get_repo_reader_service),
):
    workspace = workspace_service.get_by_id_or_slug(workspace_id)
    membership_service.require_membership(user.id, workspace.id)
    content_bytes = reader.read_agent_file(workspace, name, path)
    return AgentFileContent(path=path, content=content_bytes.decode("utf-8", errors="replace"))


@router.put("/{name}/files/{path:path}", status_code=status.HTTP_204_NO_CONTENT)
def write_agent_file(
    workspace_id: str,
    name: str,
    path: str,
    body: AgentFileContent,
    user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    membership_service: MembershipService = Depends(get_membership_service),
    service: AgentService = Depends(get_agent_service),
):
    workspace = workspace_service.get_by_id_or_slug(workspace_id)
    membership_service.require_membership(user.id, workspace.id)
    service.write_file(workspace, name, path, body.content.encode("utf-8"))



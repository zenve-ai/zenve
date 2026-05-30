from fastapi import APIRouter, Depends, HTTPException, status

from api.db.models import UserRecord
from api.models.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyResponse
from api.models.workspace import (
    WorkspaceCreate,
    WorkspaceCreatedResponse,
    WorkspaceGitHubConnect,
    WorkspaceInit,
    WorkspaceResponse,
    WorkspaceUpdate,
    WorkspaceWithRoleResponse,
)
from api.models.repo import AgentSummary, WorkspaceSettings
from api.services import (
    get_agent_service,
    get_api_key_service,
    get_github_service,
    get_membership_service,
    get_workspace_service,
    get_repo_reader_service,
)
from api.services.agent import AgentService
from api.services.api_key import ApiKeyService
from api.services.github import GitHubService
from api.services.membership import MembershipService
from api.services.workspace import WorkspaceService
from api.services.repo_reader import RepoReaderService
from api.utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    body: WorkspaceCreate,
    user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    api_key_service: ApiKeyService = Depends(get_api_key_service),
):
    workspace = workspace_service.create_draft(body, owner_user_id=user.id)
    workspace = workspace_service.commit_create(workspace)

    key_data = ApiKeyCreate(name="Default API Key")
    record, raw_key = api_key_service.create(workspace.id, key_data)

    base = ApiKeyResponse.model_validate(record, from_attributes=True)
    api_key_resp = ApiKeyCreated(**base.model_dump(), raw_key=raw_key)
    return WorkspaceCreatedResponse(
        **WorkspaceResponse.model_validate(workspace, from_attributes=True).model_dump(),
        api_key=api_key_resp,
    )


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: str,
    user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    membership_service: MembershipService = Depends(get_membership_service),
):
    workspace = workspace_service.get_by_id_or_slug(workspace_id)
    membership_service.require_role(user.id, workspace.id, ["owner"])
    workspace_service.delete(workspace.id)


@router.get("", response_model=list[WorkspaceWithRoleResponse])
def list_workspaces(
    user: UserRecord = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
):
    results = service.list_for_user(user.id)
    return [
        WorkspaceWithRoleResponse(
            **WorkspaceResponse.model_validate(workspace, from_attributes=True).model_dump(),
            role=role,
        )
        for workspace, role in results
    ]


@router.get("/{workspace_id}", response_model=WorkspaceWithRoleResponse)
def get_workspace(
    workspace_id: str,
    user: UserRecord = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
    membership_service: MembershipService = Depends(get_membership_service),
):
    workspace = service.get_by_id_or_slug(workspace_id)
    membership = membership_service.require_membership(user.id, workspace.id)
    return WorkspaceWithRoleResponse(
        **WorkspaceResponse.model_validate(workspace, from_attributes=True).model_dump(),
        role=membership.role,
    )


@router.post("/{workspace_id}/github/connect", response_model=WorkspaceResponse)
def github_connect(
    workspace_id: str,
    body: WorkspaceGitHubConnect,
    user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    membership_service: MembershipService = Depends(get_membership_service),
    github_service: GitHubService = Depends(get_github_service),
):
    workspace = workspace_service.get_by_id_or_slug(workspace_id)
    membership_service.require_role(user.id, workspace.id, ["owner", "admin"])
    installation_id = body.installation_id or user.github_installation_id
    if not installation_id:
        raise HTTPException(status_code=422, detail="No GitHub installation found.")
    updated = github_service.connect_workspace(workspace, installation_id, body.repo)
    return WorkspaceResponse.model_validate(updated, from_attributes=True)


@router.delete("/{workspace_id}/github/disconnect", status_code=status.HTTP_204_NO_CONTENT)
def github_disconnect(
    workspace_id: str,
    user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    membership_service: MembershipService = Depends(get_membership_service),
    github_service: GitHubService = Depends(get_github_service),
):
    workspace = workspace_service.get_by_id_or_slug(workspace_id)
    membership_service.require_role(user.id, workspace.id, ["owner", "admin"])
    github_service.disconnect(workspace)


@router.post("/{workspace_id}/init", response_model=list[AgentSummary])
def init_workspace(
    workspace_id: str,
    body: WorkspaceInit,
    user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    membership_service: MembershipService = Depends(get_membership_service),
    agent_service: AgentService = Depends(get_agent_service),
):
    workspace = workspace_service.get_by_id_or_slug(workspace_id)
    membership_service.require_role(user.id, workspace.id, ["owner", "admin"])
    return agent_service.init(workspace, body)


@router.get("/{workspace_id}/settings", response_model=WorkspaceSettings)
def get_workspace_settings(
    workspace_id: str,
    user: UserRecord = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    membership_service: MembershipService = Depends(get_membership_service),
    repo_reader: RepoReaderService = Depends(get_repo_reader_service),
):
    workspace = workspace_service.get_by_id_or_slug(workspace_id)
    membership_service.require_membership(user.id, workspace.id)
    settings = repo_reader.get_workspace_settings(workspace)
    return WorkspaceSettings.model_validate(settings)


@router.patch("/{workspace_id}", response_model=WorkspaceWithRoleResponse)
def update_workspace(
    workspace_id: str,
    body: WorkspaceUpdate,
    user: UserRecord = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
    membership_service: MembershipService = Depends(get_membership_service),
):
    workspace = service.get_by_id_or_slug(workspace_id)
    membership = membership_service.require_role(user.id, workspace.id, ["owner"])
    updated = service.update(workspace.id, body)
    return WorkspaceWithRoleResponse(
        **WorkspaceResponse.model_validate(updated, from_attributes=True).model_dump(),
        role=membership.role,
    )

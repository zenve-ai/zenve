from fastapi import APIRouter, Depends, HTTPException, status

from zenve_db.models import UserRecord
from zenve_models.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyResponse
from zenve_models.project import (
    ProjectCreate,
    ProjectCreatedResponse,
    ProjectGitHubConnect,
    ProjectResponse,
    ProjectUpdate,
    ProjectWithRoleResponse,
)
from zenve_services import (
    get_api_key_service,
    get_github_service,
    get_membership_service,
    get_project_service,
)
from zenve_services.api_key import ApiKeyService
from zenve_services.github import GitHubService
from zenve_services.membership import MembershipService
from zenve_services.project import ProjectService
from zenve_utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.post("", response_model=ProjectCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    user: UserRecord = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
    api_key_service: ApiKeyService = Depends(get_api_key_service),
):
    project = project_service.create_draft(body, owner_user_id=user.id)
    project = project_service.commit_create(project)

    key_data = ApiKeyCreate(name="Default API Key")
    record, raw_key = api_key_service.create(project.id, key_data)

    base = ApiKeyResponse.model_validate(record, from_attributes=True)
    api_key_resp = ApiKeyCreated(**base.model_dump(), raw_key=raw_key)
    return ProjectCreatedResponse(
        **ProjectResponse.model_validate(project, from_attributes=True).model_dump(),
        api_key=api_key_resp,
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    user: UserRecord = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
    membership_service: MembershipService = Depends(get_membership_service),
):
    project = project_service.get_by_id_or_slug(project_id)
    membership_service.require_role(user.id, project.id, ["owner"])
    project_service.delete(project.id)


@router.get("", response_model=list[ProjectWithRoleResponse])
def list_projects(
    user: UserRecord = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
):
    results = service.list_for_user(user.id)
    return [
        ProjectWithRoleResponse(
            **ProjectResponse.model_validate(project, from_attributes=True).model_dump(),
            role=role,
        )
        for project, role in results
    ]


@router.get("/{project_id}", response_model=ProjectWithRoleResponse)
def get_project(
    project_id: str,
    user: UserRecord = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
    membership_service: MembershipService = Depends(get_membership_service),
):
    project = service.get_by_id_or_slug(project_id)
    membership = membership_service.require_membership(user.id, project.id)
    return ProjectWithRoleResponse(
        **ProjectResponse.model_validate(project, from_attributes=True).model_dump(),
        role=membership.role,
    )


@router.post("/{project_id}/github/connect", response_model=ProjectResponse)
def github_connect(
    project_id: str,
    body: ProjectGitHubConnect,
    user: UserRecord = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
    membership_service: MembershipService = Depends(get_membership_service),
    github_service: GitHubService = Depends(get_github_service),
):
    project = project_service.get_by_id_or_slug(project_id)
    membership_service.require_role(user.id, project.id, ["owner", "admin"])
    installation_id = body.installation_id or user.github_installation_id
    if not installation_id:
        raise HTTPException(status_code=422, detail="No GitHub installation found.")
    updated = github_service.connect_project(project, installation_id, body.repo)
    return ProjectResponse.model_validate(updated, from_attributes=True)



@router.delete("/{project_id}/github/disconnect", status_code=status.HTTP_204_NO_CONTENT)
def github_disconnect(
    project_id: str,
    user: UserRecord = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
    membership_service: MembershipService = Depends(get_membership_service),
    github_service: GitHubService = Depends(get_github_service),
):
    project = project_service.get_by_id_or_slug(project_id)
    membership_service.require_role(user.id, project.id, ["owner", "admin"])
    github_service.disconnect(project)


@router.patch("/{project_id}", response_model=ProjectWithRoleResponse)
def update_project(
    project_id: str,
    body: ProjectUpdate,
    user: UserRecord = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
    membership_service: MembershipService = Depends(get_membership_service),
):
    project = service.get_by_id_or_slug(project_id)
    membership = membership_service.require_role(user.id, project.id, ["owner"])
    updated = service.update(project.id, body)
    return ProjectWithRoleResponse(
        **ProjectResponse.model_validate(updated, from_attributes=True).model_dump(),
        role=membership.role,
    )

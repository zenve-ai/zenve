from fastapi import APIRouter, Depends, status

from zenve_db.models import UserRecord
from zenve_models.agent import AgentCreate, AgentFileContent, AgentFileList, AgentUpdate
from zenve_models.repo import AgentDetail, AgentSummary, RunDetail, RunSummary
from zenve_services import (
    get_agent_service,
    get_membership_service,
    get_project_service,
    get_repo_reader_service,
)
from zenve_services.agent import AgentService
from zenve_services.membership import MembershipService
from zenve_services.project import ProjectService
from zenve_services.repo_reader import RepoReaderService
from zenve_utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/projects/{project_id}/agents", tags=["agents"])


@router.get("", response_model=list[AgentSummary])
def list_agents(
    project_id: str,
    user: UserRecord = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
    membership_service: MembershipService = Depends(get_membership_service),
    service: AgentService = Depends(get_agent_service),
):
    project = project_service.get_by_id_or_slug(project_id)
    membership_service.require_membership(user.id, project.id)
    return service.list(project)


@router.post("", response_model=AgentDetail, status_code=status.HTTP_201_CREATED)
def create_agent(
    project_id: str,
    body: AgentCreate,
    user: UserRecord = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
    membership_service: MembershipService = Depends(get_membership_service),
    service: AgentService = Depends(get_agent_service),
):
    project = project_service.get_by_id_or_slug(project_id)
    membership_service.require_membership(user.id, project.id)
    return service.create(project, body)


@router.get("/{name}", response_model=AgentDetail)
def get_agent(
    project_id: str,
    name: str,
    user: UserRecord = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
    membership_service: MembershipService = Depends(get_membership_service),
    service: AgentService = Depends(get_agent_service),
):
    project = project_service.get_by_id_or_slug(project_id)
    membership_service.require_membership(user.id, project.id)
    return service.get(project, name)


@router.patch("/{name}", response_model=AgentDetail)
def update_agent(
    project_id: str,
    name: str,
    body: AgentUpdate,
    user: UserRecord = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
    membership_service: MembershipService = Depends(get_membership_service),
    service: AgentService = Depends(get_agent_service),
):
    project = project_service.get_by_id_or_slug(project_id)
    membership_service.require_membership(user.id, project.id)
    return service.update(project, name, body)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    project_id: str,
    name: str,
    user: UserRecord = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
    membership_service: MembershipService = Depends(get_membership_service),
    service: AgentService = Depends(get_agent_service),
):
    project = project_service.get_by_id_or_slug(project_id)
    membership_service.require_membership(user.id, project.id)
    service.delete(project, name)


@router.get("/{name}/files", response_model=AgentFileList)
def list_agent_files(
    project_id: str,
    name: str,
    user: UserRecord = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
    membership_service: MembershipService = Depends(get_membership_service),
    reader: RepoReaderService = Depends(get_repo_reader_service),
):
    project = project_service.get_by_id_or_slug(project_id)
    membership_service.require_membership(user.id, project.id)
    return AgentFileList(files=reader.list_agent_files(project, name))


@router.get("/{name}/files/{path:path}", response_model=AgentFileContent)
def read_agent_file(
    project_id: str,
    name: str,
    path: str,
    user: UserRecord = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
    membership_service: MembershipService = Depends(get_membership_service),
    reader: RepoReaderService = Depends(get_repo_reader_service),
):
    project = project_service.get_by_id_or_slug(project_id)
    membership_service.require_membership(user.id, project.id)
    content_bytes = reader.read_agent_file(project, name, path)
    return AgentFileContent(path=path, content=content_bytes.decode("utf-8", errors="replace"))


@router.put("/{name}/files/{path:path}", status_code=status.HTTP_204_NO_CONTENT)
def write_agent_file(
    project_id: str,
    name: str,
    path: str,
    body: AgentFileContent,
    user: UserRecord = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
    membership_service: MembershipService = Depends(get_membership_service),
    service: AgentService = Depends(get_agent_service),
):
    project = project_service.get_by_id_or_slug(project_id)
    membership_service.require_membership(user.id, project.id)
    service.write_file(project, name, path, body.content.encode("utf-8"))


@router.get("/{name}/runs", response_model=list[RunSummary])
def list_agent_runs(
    project_id: str,
    name: str,
    user: UserRecord = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
    membership_service: MembershipService = Depends(get_membership_service),
    reader: RepoReaderService = Depends(get_repo_reader_service),
):
    project = project_service.get_by_id_or_slug(project_id)
    membership_service.require_membership(user.id, project.id)
    return reader.list_runs(project, name)


@router.get("/{name}/runs/{run_id}", response_model=RunDetail)
def get_agent_run(
    project_id: str,
    name: str,
    run_id: str,
    user: UserRecord = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
    membership_service: MembershipService = Depends(get_membership_service),
    reader: RepoReaderService = Depends(get_repo_reader_service),
):
    project = project_service.get_by_id_or_slug(project_id)
    membership_service.require_membership(user.id, project.id)
    return reader.get_run(project, name, run_id)

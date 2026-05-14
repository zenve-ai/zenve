from fastapi import APIRouter, Depends, status

from runtime.models.run import AgentStats
from runtime.models.workspace import AgentSummary, ScaffoldWorkspaceBody, Workspace, WorkspaceCreate, WorkspaceDetail
from runtime.services import get_template_service, get_workspace_service
from runtime.services.template_service import TemplateService
from runtime.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])


@router.post("", response_model=Workspace, status_code=status.HTTP_201_CREATED)
def register_workspace(
    body: WorkspaceCreate,
    service: WorkspaceService = Depends(get_workspace_service),
):
    return service.register(body)


@router.post("/init", response_model=Workspace, status_code=status.HTTP_201_CREATED)
def init_workspace(
    body: ScaffoldWorkspaceBody,
    service: WorkspaceService = Depends(get_workspace_service),
    template_svc: TemplateService = Depends(get_template_service),
):
    return service.scaffold(body, template_svc)


@router.get("", response_model=list[Workspace])
def list_workspaces(
    service: WorkspaceService = Depends(get_workspace_service),
):
    return service.list()


@router.get("/{workspace_id}", response_model=WorkspaceDetail)
def get_workspace(
    workspace_id: str,
    service: WorkspaceService = Depends(get_workspace_service),
):
    return service.detail(workspace_id)


@router.get("/{workspace_id}/agents", response_model=list[AgentSummary])
def list_agents(
    workspace_id: str,
    service: WorkspaceService = Depends(get_workspace_service),
):
    return service.list_agents(workspace_id)


@router.get("/{workspace_id}/agents/{agent_slug}/stats", response_model=AgentStats)
def get_agent_stats(
    workspace_id: str,
    agent_slug: str,
    service: WorkspaceService = Depends(get_workspace_service),
):
    return service.get_agent_stats(workspace_id, agent_slug)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def unregister_workspace(
    workspace_id: str,
    service: WorkspaceService = Depends(get_workspace_service),
):
    service.unregister(workspace_id)

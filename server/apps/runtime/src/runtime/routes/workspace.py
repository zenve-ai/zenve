from fastapi import APIRouter, Depends, status

from zenve_models.workspace import Workspace, WorkspaceCreate, WorkspaceDetail
from zenve_services import get_workspace_service
from zenve_services.workspace_service import WorkspaceService

router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])


@router.post("", response_model=Workspace, status_code=status.HTTP_201_CREATED)
def register_workspace(
    body: WorkspaceCreate,
    service: WorkspaceService = Depends(get_workspace_service),
):
    return service.register(body)


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


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def unregister_workspace(
    workspace_id: str,
    service: WorkspaceService = Depends(get_workspace_service),
):
    service.unregister(workspace_id)

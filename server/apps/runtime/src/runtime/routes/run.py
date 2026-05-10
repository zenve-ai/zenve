from fastapi import APIRouter, Depends

from runtime.models.run import WorkspaceRunDetail, WorkspaceRunSummary
from runtime.services import get_run_service
from runtime.services.run_service import RunService

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/runs", tags=["runs"])


@router.get("", response_model=list[WorkspaceRunSummary])
def list_runs(
    workspace_id: str,
    agent: str | None = None,
    limit: int = 50,
    service: RunService = Depends(get_run_service),
):
    return service.list_for_workspace(workspace_id, agent=agent, limit=limit)


@router.get("/{run_id}", response_model=WorkspaceRunDetail)
def get_run(
    workspace_id: str,
    run_id: str,
    service: RunService = Depends(get_run_service),
):
    return service.get(workspace_id, run_id)

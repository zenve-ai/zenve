from fastapi import APIRouter, Depends

from runtime.models.errors import NotFoundError
from runtime.models.run import (
    RunTriggerRequest,
    RunTriggerResponse,
    WorkspaceRun,
)
from runtime.run_store import RunStore
from runtime.services import get_run_service, get_run_store, get_trigger_service
from runtime.services.run_service import RunService
from runtime.services.run_trigger_service import RunTriggerService

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/runs", tags=["runs"])


@router.post("", response_model=RunTriggerResponse, status_code=202)
def trigger_run(
    workspace_id: str,
    body: RunTriggerRequest,
    service: RunTriggerService = Depends(get_trigger_service),
):
    return service.trigger(workspace_id, body)


@router.get("", response_model=list[WorkspaceRun])
def list_runs(
    workspace_id: str,
    limit: int = 50,
    service: RunService = Depends(get_run_service),
):
    return service.list_grouped(workspace_id, limit=limit)


@router.get("/active-run")
def get_active_run(
    workspace_id: str,
    run_store: RunStore = Depends(get_run_store),
):
    record = run_store.get_active_for_workspace(workspace_id)
    if record is None:
        raise NotFoundError("No active run for this workspace")
    return {"run_id": record.run_id, "status": record.status}


@router.get("/{run_id}", response_model=WorkspaceRun)
def get_run(
    workspace_id: str,
    run_id: str,
    service: RunService = Depends(get_run_service),
):
    return service.get_grouped(workspace_id, run_id)


@router.get("/{run_id}/events", response_model=list[dict])
def get_run_events(
    workspace_id: str,
    run_id: str,
    service: RunService = Depends(get_run_service),
):
    return service.get_events(workspace_id, run_id)
